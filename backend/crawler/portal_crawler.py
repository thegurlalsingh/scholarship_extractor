"""
Recursively crawls a single scholarship portal up to a configured depth and page limit.

Starts from a seed URL, fetches each page, classifies it as a listing or detail page,
extracts scholarships, then follows internal links to the next depth level. Listing pages
(which contain multiple scheme entries in a table or list) are allowed to use the LLM
fallback extractor. Detail pages (individual scheme pages) use only deterministic parsing
to keep unattended crawl runs from making LLM calls at scale.
"""

from typing import Set
from urllib.parse import urlparse

from .page_crawler import PageCrawler
from .page_classifier import PageClassifier
from .scholarship_extractor import ScholarshipExtractor


class PortalCrawler:

    def __init__(self, page_crawler: PageCrawler, max_depth: int = 2, max_pages: int = 20):
        self.page_crawler = page_crawler
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.page_classifier = PageClassifier()
        self.scholarship_extractor = ScholarshipExtractor()
        self.visited: Set[str] = set()
        self.potential_scholarships = []

    def crawl(self, start_url: str):
        results = []
        self.visited.clear()
        self.potential_scholarships = []

        queue = [(self._normalize_url(start_url), 0, None)]

        while queue and len(results) < self.max_pages:
            url, depth, parent_url = queue.pop(0)

            if url in self.visited:
                continue

            self.visited.add(url)
            print(f"[PortalCrawler] Depth={depth} → {url}")

            page = self.page_crawler.crawl(url)
            if not page:
                continue

            final_url = self._normalize_url(page.get("url", url))
            page["url"] = final_url
            page["depth"] = depth
            page["parent_url"] = parent_url
            results.append(page)

            page_type = self.page_classifier.classify(page)
            page["page_type"] = page_type
            print(f"[PortalCrawler] Page Type → {page_type}")

            if page_type == PageClassifier.SCHOLARSHIP_LISTING:
                print("[PortalCrawler] Scholarship listing detected.")
                scholarships = self.scholarship_extractor.extract(page, use_llm_fallback=True)
                self.potential_scholarships.extend(scholarships)
                print(f"[PortalCrawler] Extracted {len(scholarships)} potential scholarships.")
                continue

            if page_type == PageClassifier.SCHOLARSHIP_DETAIL:
                scholarships = self.scholarship_extractor.extract(page, use_llm_fallback=False)
                if scholarships:
                    self.potential_scholarships.extend(scholarships)
                    print(f"[PortalCrawler] Extracted {len(scholarships)} potential scholarships from detail page.")

            if depth >= self.max_depth:
                continue

            for link in page.get("links", []):
                normalized_link = self._normalize_url(link)
                if not normalized_link:
                    continue
                if normalized_link in self.visited:
                    continue
                already_queued = any(q_url == normalized_link for q_url, _, _ in queue)
                if already_queued:
                    continue
                queue.append((normalized_link, depth + 1, final_url))

        self.potential_scholarships = self._deduplicate_scholarships(self.potential_scholarships)
        print(
            f"[PortalCrawler] Finished. "
            f"Visited={len(self.visited)}, Pages={len(results)}, "
            f"Potential Scholarships={len(self.potential_scholarships)}"
        )
        return results

    def get_potential_scholarships(self):
        return self.potential_scholarships

    @staticmethod
    def _deduplicate_scholarships(scholarships):
        seen = set()
        result = []
        for scholarship in scholarships:
            title = scholarship.get("title", "").strip().lower()
            source_url = scholarship.get("source_url", "").strip().lower()
            key = (title, source_url)
            if key in seen:
                continue
            seen.add(key)
            result.append(scholarship)
        return result

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        parsed = urlparse(url)
        parsed = parsed._replace(fragment="")
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        port = parsed.port
        if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            hostname = f"{hostname}:{port}"
        normalized = f"{scheme}://{hostname}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.rstrip("/")