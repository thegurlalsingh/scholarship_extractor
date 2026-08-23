"""
Thin persistence layer between the crawling pipeline and Supabase PostgreSQL.

Provides two store implementations: SupabaseStore (live database) and NullStore
(dry-run no-op used when credentials are missing or --skip-db is passed). The
interface is identical between both, so callers never need to check which one
they have. All date values are normalized from DD-MM-YYYY to ISO YYYY-MM-DD
before writing so that Postgres DATE columns are unambiguous regardless of
the server's DateStyle setting.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

def _to_iso_date(value: Optional[str]) -> Optional[str]:
    """
    Extractor/LLM produce dates as 'DD-MM-YYYY'. Postgres DATE columns
    should get unambiguous ISO 'YYYY-MM-DD' strings on insert rather than
    relying on the server's DateStyle setting to guess DD-MM vs MM-DD.
    Returns None if the value is missing or unparseable (so it lands as
    SQL NULL instead of crashing the insert).
    """

    if not value:
        return None

    value = str(value).strip()

    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    print(f"[SupabaseStore] Could not parse date '{value}', storing NULL.")
    return None


# ==============================================================
# NULL STORE (dry-run / no credentials)
# ==============================================================

class NullStore:
    """
    Drop-in no-op replacement for SupabaseStore. Used when SUPABASE_URL /
    SUPABASE_SERVICE_ROLE_KEY aren't set, or when the orchestrator is run
    with --skip-db. Hands out fake incrementing ids so the rest of the
    pipeline (which expects ids back) runs unmodified, but nothing is
    written anywhere.
    """

    def __init__(self):
        self._counter = 0
        print(
            "[NullStore] Running WITHOUT a database connection. "
            "Nothing will be persisted to Supabase."
        )

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def start_discovery_run(self, total_queries: int) -> int:
        return self._next_id()

    def finish_discovery_run(self, *args, **kwargs) -> None:
        return None

    def insert_discovery_candidates(self, run_id, candidates) -> Dict[str, int]:
        return {c.url: self._next_id() for c in candidates}

    def start_crawl_run(self, *args, **kwargs) -> int:
        return self._next_id()

    def finish_crawl_run(self, *args, **kwargs) -> None:
        return None

    def insert_crawl_pages(self, crawl_run_id, pages) -> Dict[str, int]:
        return {p["url"]: self._next_id() for p in pages}

    def insert_scholarships(self, crawl_run_id, scholarships, page_id_by_url) -> Dict[Tuple[str, str], int]:
        out = {}
        for s in scholarships:
            key = ((s.get("title") or "").strip().lower(), (s.get("source_url") or "").strip().lower())
            out[key] = self._next_id()
        return out

    def insert_validation(self, scholarship_id, validation_record) -> Optional[int]:
        return self._next_id()

    def get_scholarships_due_for_recheck(self, *args, **kwargs) -> List[dict]:
        print("[NullStore] No database connected - nothing to recheck.")
        return []

    def update_scholarship_after_recheck(self, *args, **kwargs) -> None:
        return None

    def insert_scholarship_changes(self, changes) -> None:
        return None

    def start_recheck_run(self, *args, **kwargs) -> int:
        return self._next_id()

    def finish_recheck_run(self, *args, **kwargs) -> None:
        return None

    def get_last_recheck_run(self) -> Optional[dict]:
        return None




class SupabaseStore:

    def __init__(self):

        from supabase import create_client, Client  # local import, see module docstring

        url = os.environ.get("SUPABASE_URL")
        key = (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_KEY")
        )

        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) "
                "must be set in the environment to use SupabaseStore."
            )

        self.client: "Client" = create_client(url, key)



    def start_discovery_run(self, total_queries: int) -> int:

        row = {
            "status": "RUNNING",
            "total_queries": total_queries,
        }

        result = self.client.table("discovery_runs").insert(row).execute()

        run_id = result.data[0]["id"]

        print(f"[SupabaseStore] Created discovery_run id={run_id}")

        return run_id

    def finish_discovery_run(
        self,
        run_id: int,
        total_results: int,
        total_candidates: int,
        status: str = "COMPLETED",
    ) -> None:

        self.client.table("discovery_runs").update({
            "status": status,
            "total_results": total_results,
            "total_candidates": total_candidates,
            "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }).eq("id", run_id).execute()



    def insert_discovery_candidates(self, run_id: int, candidates: List[Any]) -> Dict[str, int]:
        """
        candidates: List[ScholarshipCandidate]
        Returns: {url: discovery_candidate_id}
        """

        if not candidates:
            return {}

        rows = []

        for c in candidates:
            rows.append({
                "discovery_run_id": run_id,
                "title": c.title or "",
                "url": c.url,
                "domain": c.domain or "",
                "snippet": c.snippet,
                "discovery_query": c.discovery_query,
                "discovered_from": c.discovered_from,
                "source_type": c.source_type,
                "candidate_type": c.candidate_type,
                "is_official_source": c.is_official_source,
            })

        result = self.client.table("discovery_candidates").insert(rows).execute()

        url_to_id = {}

        for row in result.data:
            url_to_id[row["url"]] = row["id"]

        print(f"[SupabaseStore] Inserted {len(url_to_id)} discovery_candidates")

        return url_to_id

    # ==========================================================
    # CRAWL RUNS
    # ==========================================================

    def start_crawl_run(
        self,
        discovery_candidate_id: Optional[int],
        start_url: str,
        max_depth: int,
        max_pages: int,
    ) -> int:

        row = {
            "discovery_candidate_id": discovery_candidate_id,
            "start_url": start_url,
            "max_depth": max_depth,
            "max_pages": max_pages,
            "status": "RUNNING",
        }

        result = self.client.table("crawl_runs").insert(row).execute()

        run_id = result.data[0]["id"]

        print(f"[SupabaseStore] Created crawl_run id={run_id} for {start_url}")

        return run_id

    def finish_crawl_run(
        self,
        run_id: int,
        total_pages_visited: int,
        total_pages_failed: int,
        total_scholarships_extracted: int,
        status: str = "COMPLETED",
    ) -> None:

        self.client.table("crawl_runs").update({
            "status": status,
            "total_pages_visited": total_pages_visited,
            "total_pages_failed": total_pages_failed,
            "total_scholarships_extracted": total_scholarships_extracted,
            "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }).eq("id", run_id).execute()



    def insert_crawl_pages(self, crawl_run_id: int, pages: List[dict]) -> Dict[str, int]:
        """
        pages: list of dicts already shaped by orchestrator._build_page_record()
        Returns: {url: crawl_page_id}
        """

        if not pages:
            return {}

        rows = []

        for p in pages:
            rows.append({
                "crawl_run_id": crawl_run_id,
                "url": p["url"],
                "final_url": p.get("final_url"),
                "depth": p.get("depth", 0),
                "title": p.get("title"),
                "status_code": p.get("status_code"),
                "page_type": p.get("page_type"),
                "crawl_status": p.get("crawl_status", "CRAWLED"),
                "crawl_action": p.get("crawl_action"),
                "skip_reason": p.get("skip_reason"),
                "links_found": p.get("links_found", 0),
                "links_queued": p.get("links_queued", 0),
                "scholarships_extracted": p.get("scholarships_extracted", 0),
                "extraction_method": p.get("extraction_method"),
                "decision_metadata": p.get("decision_metadata"),
                "error_message": p.get("error_message"),
                "crawled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            })

        result = self.client.table("crawl_pages").insert(rows).execute()

        url_to_id = {}

        for row in result.data:
            url_to_id[row["url"]] = row["id"]

        print(f"[SupabaseStore] Inserted {len(url_to_id)} crawl_pages")

        return url_to_id



    def insert_scholarships(
        self,
        crawl_run_id: int,
        scholarships: List[dict],
        page_id_by_url: Dict[str, int],
    ) -> Dict[Tuple[str, str], int]:
        """
        scholarships: raw scholarship dicts from ScholarshipExtractor
        page_id_by_url: {crawl_page.url: crawl_page.id} from insert_crawl_pages
        Returns: {(title_lower, source_url_lower): scholarship_id}
        """

        if not scholarships:
            return {}

        rows = []

        for s in scholarships:

            source_url = (s.get("source_url") or "").strip()
            end_date_str = _to_iso_date(s.get("application_end"))
            computed_status = 'ACTIVE'
            if end_date_str:
                from datetime import date
                try:
                    end_date = date.fromisoformat(end_date_str)
                    today = date.today()
                    delta = (end_date - today).days
                    if delta < 0:
                        computed_status = 'EXPIRED'
                    elif delta <= 7:
                        computed_status = 'EXPIRING_SOON'
                except Exception:
                    pass

            rows.append({
                "crawl_run_id": crawl_run_id,
                "crawl_page_id": page_id_by_url.get(source_url.rstrip("/")),
                "title": s.get("title") or "Untitled scholarship",
                "organization": s.get("organization"),
                "scheme_type": s.get("scheme_type"),
                "application_start": _to_iso_date(s.get("application_start")),
                "application_end": end_date_str,
                "source_url": source_url,
                "guidelines_url": s.get("guidelines_url"),
                "faq_url": s.get("faq_url"),
                "application_url": s.get("application_url"),
                "scholarship_amount": s.get("scholarship_amount"),
                "education_level": s.get("education_level"),
                "income_criteria": s.get("income_criteria"),
                "gender_criteria": s.get("gender_criteria"),
                "category_criteria": s.get("category_criteria"),
                "domicile": s.get("domicile"),
                "eligibility_summary": s.get("eligibility_summary"),
                "documents_required": s.get("documents_required"),
                "selection_process": s.get("selection_process"),
                "computed_status": computed_status
            })

        result = self.client.table("scholarships").insert(rows).execute()

        key_to_id = {}

        for row in result.data:
            key = (row["title"].strip().lower(), row["source_url"].strip().lower())
            key_to_id[key] = row["id"]

        print(f"[SupabaseStore] Inserted {len(key_to_id)} scholarships")

        return key_to_id



    def insert_validation(self, scholarship_id, validation_record) -> Optional[int]:
        """
        validation_record: the full dict returned by ScholarshipValidator.validate()
        i.e. {"validation": {...}, "scholarship": {...}, "source": {...},
              "verification_checks": [...], "warnings": [...]}
        """

        if scholarship_id is None:
            print(
                "[SupabaseStore] Skipping validation insert - "
                "no matching scholarship_id found."
            )
            return None

        v = validation_record["validation"]

        row = {
            "scholarship_id": scholarship_id,
            "status": v["status"],
            "legitimacy_score": v["legitimacy_score"],
            "confidence": v["confidence"],
            "verified_at": v["verified_at"],
            "verification_checks": validation_record["verification_checks"],
            "warnings": validation_record["warnings"],
            "source_snapshot": validation_record["source"],
        }

        result = self.client.table("scholarship_validations").insert(row).execute()

        return result.data[0]["id"]



    def get_scholarships_due_for_recheck(
        self,
        stale_after_hours: int = 24,
        only_active: bool = True,
        limit: int = 500,
    ) -> List[dict]:
        """
        Reads from scholarship_monitoring (not scholarships directly),
        then joins in the scholarship content. Returns a flat list of
        dicts: scholarship fields + monitoring fields
        (last_checked_at, consecutive_failures) merged together, since
        that's what recheck_scholarships.py's diff/update logic
        expects.
        """

        from datetime import timedelta

        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=stale_after_hours)
        ).isoformat().replace("+00:00", "Z")

        mon_query = self.client.table("scholarship_monitoring").select("*")

        if only_active:
            mon_query = mon_query.eq("is_active", True)

        mon_query = mon_query.or_(
            f"last_checked_at.is.null,last_checked_at.lt.{cutoff}"
        )

        mon_rows = mon_query.limit(limit).execute().data or []

        if not mon_rows:
            return []

        scholarship_ids = [row["scholarship_id"] for row in mon_rows]
        monitoring_by_scholarship_id = {row["scholarship_id"]: row for row in mon_rows}

        sch_rows = (
            self.client.table("scholarships")
            .select("*")
            .in_("id", scholarship_ids)
            .execute()
            .data
            or []
        )

        merged = []

        for sch in sch_rows:
            mon = monitoring_by_scholarship_id.get(sch["id"], {})
            merged.append({
                **sch,
                "last_checked_at": mon.get("last_checked_at"),
                "consecutive_failures": mon.get("consecutive_failures", 0),
            })

        return merged

    def update_scholarship_after_recheck(
        self,
        scholarship_id: int,
        field_updates: Dict[str, Any],
        is_active: bool = True,
        consecutive_failures: int = 0,
    ) -> None:
        """
        field_updates (title/dates/links/etc.) go to `scholarships`.
        Monitoring metadata (last_checked_at/is_active/failures) goes
        to `scholarship_monitoring` - the trg_sync_active_status
        trigger propagates is_active back onto `scholarships`
        automatically, so it isn't set here directly.
        """

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if field_updates:
            content_update = dict(field_updates)
            content_update["updated_at"] = now
            self.client.table("scholarships").update(content_update).eq(
                "id", scholarship_id
            ).execute()

        self.client.table("scholarship_monitoring").update({
            "last_checked_at": now,
            "is_active": is_active,
            "consecutive_failures": consecutive_failures,
            "updated_at": now,
        }).eq("scholarship_id", scholarship_id).execute()

    def insert_scholarship_changes(self, changes: List[dict]) -> None:
        """
        changes: list of
            {"scholarship_id": int, "field_name": str,
             "old_value": Optional[str], "new_value": Optional[str],
             "change_type": "FIELD_UPDATED" | "MARKED_INACTIVE" | "REACTIVATED"}
        """

        if not changes:
            return

        self.client.table("scholarship_changes").insert(changes).execute()

        print(f"[SupabaseStore] Logged {len(changes)} scholarship change(s)")

    # ==========================================================
    # RECHECK RUNS
    # ==========================================================
    #
    # One row per RecheckService.run() call - i.e. one row per time
    # the cron/API actually finished processing a batch. This is what
    # a dashboard's "last updated on" should read from, NOT
    # cron.job_run_details: pg_net dispatches the HTTP call
    # asynchronously, so a cron "run" finishing just means the
    # request was queued, not that the recheck itself is done.
    # ==========================================================

    def start_recheck_run(
        self,
        batch_size: int,
        stale_after_hours: int,
        include_inactive: bool,
    ) -> int:

        row = {
            "status": "RUNNING",
            "batch_size": batch_size,
            "stale_after_hours": stale_after_hours,
            "include_inactive": include_inactive,
        }

        result = self.client.table("recheck_runs").insert(row).execute()

        run_id = result.data[0]["id"]

        print(f"[SupabaseStore] Created recheck_run id={run_id}")

        return run_id

    def finish_recheck_run(
        self,
        run_id: int,
        summary: Dict[str, Any],
        status: str = "COMPLETED",
    ) -> None:
        """
        summary: the dict RecheckService.run() builds up, e.g.
            {"checked": .., "still_active": .., "reactivated": ..,
             "marked_inactive": .., "fetch_failed": ..,
             "fields_updated": .., "errors": ..}
        """

        self.client.table("recheck_runs").update({
            "status": status,
            "total_checked": summary.get("checked", 0),
            "total_still_active": summary.get("still_active", 0),
            "total_reactivated": summary.get("reactivated", 0),
            "total_marked_inactive": summary.get("marked_inactive", 0),
            "total_fetch_failed": summary.get("fetch_failed", 0),
            "total_fields_updated": summary.get("fields_updated", 0),
            "total_errors": summary.get("errors", 0),
            "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }).eq("id", run_id).execute()

    def get_last_recheck_run(self) -> Optional[dict]:
        """
        For a dashboard's "last updated on" indicator. Only looks at
        COMPLETED runs, so a run that's currently RUNNING (or crashed
        mid-way and got marked FAILED) never displays as the latest
        successful check.
        """

        result = (
            self.client.table("recheck_runs")
            .select("*")
            .eq("status", "COMPLETED")
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )

        rows = result.data or []

        return rows[0] if rows else None


# ==============================================================
# FACTORY
# ==============================================================

def get_store(skip_db: bool = False):
    """
    Returns a SupabaseStore if credentials are available and skip_db is
    False, otherwise falls back to NullStore so the pipeline can still run
    end-to-end (e.g. for local testing) without a database.
    """

    if skip_db:
        return NullStore()

    if not os.environ.get("SUPABASE_URL") or not (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    ):
        print(
            "[SupabaseStore] SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set - "
            "falling back to NullStore (no persistence)."
        )
        return NullStore()

    try:
        return SupabaseStore()
    except Exception as exc:
        print(f"[SupabaseStore] Failed to initialize Supabase client: {exc}")
        print("[SupabaseStore] Falling back to NullStore (no persistence).")
        return NullStore()