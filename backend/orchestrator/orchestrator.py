"""
End-to-end pipeline orchestrator.

Executes the full pipeline sequentially:
1. DISCOVERY  - Searches the web for candidate scholarship sources.
2. FILTER     - Keeps only candidates worth crawling (SCHOLARSHIP / PORTAL).
3. CRAWL      - Crawls each candidate site, extracting potential scholarships.
4. VERIFY     - Drops any extracted scholarship whose title doesn't literally appear on the page (anti-hallucination).
5. VALIDATE   - Scores and verifies each surviving scholarship based on evidence.
6. PERSIST    - Writes everything to Supabase.
"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from discovery.discovery_engine import DiscoveryEngine
from discovery.search_provider import WebSearchProvider
from discovery.source_classifier import SourceClassifier
from discovery.candidate_classifier import CandidateClassifier
from discovery.candidate import ScholarshipCandidate

from crawler.link_extractor import LinkExtractor
from crawler.page_crawler import PageCrawler
from crawler.portal_crawler import PortalCrawler
from crawler.page_classifier import PageClassifier

from validator.scholarship_validator import ScholarshipValidator

from database.supabase import get_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")



# KNOWN LISTING URL OVERRIDES

#
# Discovery finds candidates via web search, which often returns a
# domain's homepage rather than its actual scholarship listing page
# (e.g. search returns "scholarships.gov.in" instead of
# "scholarships.gov.in/All-Scholarships"). For a handful of well-known
# official portals we already know the correct entry point - use it
# instead of wasting a crawl on a homepage that has none of the real
# scheme data. Extend this as you discover more.

KNOWN_LISTING_URLS: Dict[str, str] = {
    "scholarships.gov.in": "https://scholarships.gov.in/All-Scholarships",
    "pmsonline.bihar.gov.in": "https://pmsonline.bihar.gov.in/pms/pms_online/Default.aspx",
}


def resolve_start_url(url: str, domain: str) -> str:

    override = KNOWN_LISTING_URLS.get(domain)

    if override and override.rstrip("/") != url.rstrip("/"):
        print(
            f"[Orchestrator] Overriding discovered URL for known domain "
            f"'{domain}': {url} -> {override}"
        )
        return override

    return url



# CANDIDATE SELECTION


CRAWLABLE_CANDIDATE_TYPES = {"SCHOLARSHIP", "PORTAL"}


def select_candidates_to_crawl(
    candidates: List[ScholarshipCandidate],
    max_domains: int,
) -> List[ScholarshipCandidate]:

    seen_domains = set()
    selected = []

    for candidate in candidates:

        if candidate.candidate_type not in CRAWLABLE_CANDIDATE_TYPES:
            continue

        domain = candidate.domain or ""

        if domain in seen_domains:
            continue

        seen_domains.add(domain)
        selected.append(candidate)

        if len(selected) >= max_domains:
            break

    return selected



# ANTI-HALLUCINATION FILTER


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "")).strip().lower()


def verify_scholarships_against_source(
    scholarships: List[dict],
    pages: List[dict],
) -> Tuple[List[dict], List[dict]]:
    """
    Deterministic extraction always pulls the title straight out of the
    page's own HTML, so it can never fail this check. The LLM fallback
    is the risk: given a thin/JS-rendered page with little real content,
    a small free-tier model can invent plausible-sounding scholarship
    names instead of correctly returning nothing.

    This is a blunt but effective guard: if a scholarship's title text
    doesn't literally appear anywhere in the page it claims to be
    extracted from, it's almost certainly fabricated (or paraphrased
    from training knowledge, not from what's on the page) - drop it
    rather than store/serve something that isn't actually on the site.

    Returns (verified, dropped).
    """

    page_text_by_url = {
        p["url"].rstrip("/"): _normalize(p.get("text", ""))
        for p in pages
    }

    verified = []
    dropped = []

    for s in scholarships:

        source_url = (s.get("source_url") or "").rstrip("/")
        title = _normalize(s.get("title", ""))

        page_text = page_text_by_url.get(source_url, "")

        if title and title in page_text:
            verified.append(s)
        else:
            dropped.append(s)
            print(
                f"[Orchestrator] DROPPING unverifiable scholarship "
                f"(title not found on {source_url or '(unknown source)'}): "
                f"{s.get('title')!r}"
            )

    return verified, dropped



# CRAWL PAGE RECORD BUILDER


def build_page_records(
    pages: List[dict],
    scholarships: List[dict],
    max_depth: int,
) -> List[dict]:

    scholarships_by_source_url: Dict[str, int] = defaultdict(int)

    for s in scholarships:
        key = (s.get("source_url") or "").rstrip("/")
        scholarships_by_source_url[key] += 1

    records = []

    for page in pages:

        url = page.get("url", "")
        depth = page.get("depth", 0)
        page_type = page.get("page_type", PageClassifier.NORMAL_PAGE)

        if page_type == PageClassifier.SCHOLARSHIP_LISTING:
            crawl_action = "EXTRACT_SCHOLARSHIPS"
        elif page_type == PageClassifier.SCHOLARSHIP_DETAIL:
            crawl_action = "EXTRACT_SCHOLARSHIPS"
        elif depth >= max_depth:
            crawl_action = "STOP_MAX_DEPTH"
        else:
            crawl_action = "FOLLOW_LINKS"

        links_found = len(page.get("links", []))
        links_queued = links_found if crawl_action == "FOLLOW_LINKS" else 0

        extracted_here = scholarships_by_source_url.get(url.rstrip("/"), 0)

        extraction_method = "DETERMINISTIC" if extracted_here > 0 else None

        records.append({
            "url": url,
            "final_url": url,
            "depth": depth,
            "title": page.get("title"),
            "status_code": page.get("status"),
            "page_type": page_type,
            "crawl_status": "CRAWLED",
            "crawl_action": crawl_action,
            "skip_reason": None,
            "links_found": links_found,
            "links_queued": links_queued,
            "scholarships_extracted": extracted_here,
            "extraction_method": extraction_method,
            "decision_metadata": {
                "parent_url": page.get("parent_url"),
            },
            "error_message": None,
        })

    return records



# PIPELINE STAGES


def run_discovery(store) -> List[ScholarshipCandidate]:

    print("\n" + "=" * 100)
    print("STAGE 1 - DISCOVERY")
    print("=" * 100)

    search_provider = WebSearchProvider(max_results=10, region="in-en")
    source_classifier = SourceClassifier()
    candidate_classifier = CandidateClassifier()

    engine = DiscoveryEngine(
        search_provider=search_provider,
        source_classifier=source_classifier,
        candidate_classifier=candidate_classifier,
    )

    from discovery.strategies import DISCOVERY_STRATEGIES
    total_queries = sum(len(s.queries) for s in DISCOVERY_STRATEGIES)

    run_id = store.start_discovery_run(total_queries)

    candidates = engine.discover()

    print(f"[Orchestrator] Discovery found {len(candidates)} raw candidates.")

    url_to_candidate_id = store.insert_discovery_candidates(run_id, candidates)

    for c in candidates:
        c_id = url_to_candidate_id.get(c.url)
        setattr(c, "_db_id", c_id)

    store.finish_discovery_run(
        run_id,
        total_results=len(candidates),
        total_candidates=len(candidates),
        status="COMPLETED",
    )

    return candidates


def run_crawl_for_candidate(
    store,
    candidate: Optional[ScholarshipCandidate],
    start_url: str,
    max_depth: int,
    max_pages: int,
) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Returns (pages, verified_scholarships, dropped_scholarships).
    """

    print("\n" + "-" * 100)
    print(f"[Orchestrator] Crawling: {start_url}")
    print("-" * 100)

    link_extractor = LinkExtractor()
    page_crawler = PageCrawler(link_extractor=link_extractor)
    portal_crawler = PortalCrawler(
        page_crawler=page_crawler,
        max_depth=max_depth,
        max_pages=max_pages,
    )

    candidate_db_id = getattr(candidate, "_db_id", None) if candidate else None

    crawl_run_id = store.start_crawl_run(
        discovery_candidate_id=candidate_db_id,
        start_url=start_url,
        max_depth=max_depth,
        max_pages=max_pages,
    )

    status = "COMPLETED"

    try:
        pages = portal_crawler.crawl(start_url)
    except Exception as exc:
        print(f"[Orchestrator] Crawl failed for {start_url}: {exc}")
        pages = []
        status = "FAILED"

    raw_scholarships = portal_crawler.get_potential_scholarships()

    verified, dropped = verify_scholarships_against_source(raw_scholarships, pages)

    total_visited = len(portal_crawler.visited)
    total_failed = max(total_visited - len(pages), 0)

    page_records = build_page_records(pages, verified, max_depth)
    url_to_page_id = store.insert_crawl_pages(crawl_run_id, page_records)

    key_to_scholarship_id = store.insert_scholarships(
        crawl_run_id,
        verified,
        url_to_page_id,
    )

    store.finish_crawl_run(
        crawl_run_id,
        total_pages_visited=total_visited,
        total_pages_failed=total_failed,
        total_scholarships_extracted=len(verified),
        status=status,
    )

    for s in verified:
        key = ((s.get("title") or "").strip().lower(), (s.get("source_url") or "").strip().lower())
        s["_db_id"] = key_to_scholarship_id.get(key)
        s["_crawl_run_id"] = crawl_run_id

    print(
        f"[Orchestrator] Done: {len(pages)} pages crawled, "
        f"{len(verified)} verified scholarships "
        f"({len(dropped)} dropped as unverifiable)."
    )

    return pages, verified, dropped


def run_validation(store, all_scholarships: List[dict]) -> List[dict]:

    print("\n" + "=" * 100)
    print("STAGE - VALIDATION")
    print("=" * 100)

    if not all_scholarships:
        print("[Orchestrator] No scholarships to validate.")
        return []

    validator = ScholarshipValidator()

    validated = validator.validate_many(all_scholarships)

    for result in validated:
        scholarship_db_id = result["scholarship"].get("_db_id")
        store.insert_validation(scholarship_db_id, result)

    return validated



# JSON EXPORT


def export_json(validated: List[dict], dropped: List[dict], output_path: str) -> None:

    clean_results = []

    for result in validated:

        scholarship = dict(result["scholarship"])
        scholarship.pop("_db_id", None)
        scholarship.pop("_crawl_run_id", None)

        clean_results.append({
            "scholarship": scholarship,
            "validation": result["validation"],
            "source": result["source"],
            "verification_checks": result["verification_checks"],
            "warnings": result["warnings"],
        })

    payload = {
        "generated_at": _now_iso(),
        "total_scholarships": len(clean_results),
        "scholarships": clean_results,
        "dropped_unverifiable_count": len(dropped),
        "dropped_unverifiable": [
            {"title": d.get("title"), "source_url": d.get("source_url")}
            for d in dropped
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    print(f"\n[Orchestrator] Saved {len(clean_results)} scholarships -> {output_path}")

    if dropped:
        print(
            f"[Orchestrator] {len(dropped)} extracted item(s) were dropped "
            f"because their title didn't appear on the source page "
            f"(likely LLM hallucination) - see 'dropped_unverifiable' in the JSON."
        )



# MAIN


def run_pipeline(
    start_url: Optional[str] = None,
    max_domains: int = 40,
    max_depth: int = 2,
    max_pages: int = 15,
    output: str = "scholarships_output.json",
    skip_db: bool = False,
) -> dict:

    started_at = time.time()

    store = get_store(skip_db=skip_db)

    all_pages: List[dict] = []
    all_scholarships: List[dict] = []
    all_dropped: List[dict] = []

    if start_url:

        print("\n[Orchestrator] --start-url provided, skipping discovery stage.")

        pages, verified, dropped = run_crawl_for_candidate(
            store,
            candidate=None,
            start_url=start_url,
            max_depth=max_depth,
            max_pages=max_pages,
        )

        all_pages.extend(pages)
        all_scholarships.extend(verified)
        all_dropped.extend(dropped)

    else:

        candidates = run_discovery(store)

        print("\n" + "=" * 100)
        print("STAGE 2 - CRAWLING")
        print("=" * 100)

        selected = select_candidates_to_crawl(candidates, max_domains=max_domains)

        print(
            f"[Orchestrator] Selected {len(selected)} candidate(s) to crawl "
            f"(out of {len(candidates)} discovered)."
        )

        if not selected:
            print(
                "[Orchestrator] No crawlable candidates (SCHOLARSHIP/PORTAL) "
                "were discovered. Nothing to crawl or validate."
            )

        for candidate in selected:

            start_url_resolved = resolve_start_url(candidate.url, candidate.domain or "")

            pages, verified, dropped = run_crawl_for_candidate(
                store,
                candidate=candidate,
                start_url=start_url_resolved,
                max_depth=max_depth,
                max_pages=max_pages,
            )

            all_pages.extend(pages)
            all_scholarships.extend(verified)
            all_dropped.extend(dropped)

    validated = run_validation(store, all_scholarships)

    export_json(validated, all_dropped, output)

    elapsed = time.time() - started_at

    print("\n" + "=" * 100)
    print("PIPELINE COMPLETE")
    print("=" * 100)
    print(f"Pages crawled                 : {len(all_pages)}")
    print(f"Scholarships verified         : {len(all_scholarships)}")
    print(f"Scholarships dropped (unverif): {len(all_dropped)}")
    print(f"Scholarships validated        : {len(validated)}")
    print(f"Elapsed time                  : {elapsed:.1f}s")
    print(f"JSON output                   : {output}")

    by_status = defaultdict(int)
    if validated:
        for r in validated:
            by_status[r["validation"]["status"]] += 1
        print("\nValidation status breakdown:")
        for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
            print(f"  {status:16s}: {count}")

    return {
        "pages_crawled": len(all_pages),
        "scholarships_verified": len(all_scholarships),
        "scholarships_dropped": len(all_dropped),
        "scholarships_validated": len(validated),
        "elapsed_time_seconds": elapsed,
        "validation_status_breakdown": dict(by_status),
        "output_path": output,
    }


def main():

    parser = argparse.ArgumentParser(
        description="Discover, crawl, extract, verify, validate, and store scholarships."
    )

    parser.add_argument("--start-url", default=None, help="Skip discovery and crawl only this URL.")
    parser.add_argument("--max-domains", type=int, default=40)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=15)
    parser.add_argument("--output", default="scholarships_output.json")
    parser.add_argument("--skip-db", action="store_true")

    args = parser.parse_args()

    run_pipeline(
        start_url=args.start_url,
        max_domains=args.max_domains,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        output=args.output,
        skip_db=args.skip_db,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Orchestrator] Interrupted by user.")
        sys.exit(1)
