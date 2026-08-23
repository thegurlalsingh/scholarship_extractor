"""
Periodic worker that re-verifies scholarships already in the database.

For each scholarship due for a recheck, the worker re-fetches its source URL, confirms
the scheme title still appears on the page, and diffs tracked fields against what is
stored. Changed fields are written back to the database and logged as FIELD_UPDATED rows.
Scholarships that fail to load 3 times in a row are marked NO_LONGER_VERIFIABLE and
deactivated. Previously inactive scholarships that become reachable again are logged
as REACTIVATED.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from crawler.link_extractor import LinkExtractor
from crawler.page_crawler import PageCrawler
from crawler.scholarship_extractor import ScholarshipExtractor

from database.supabase import get_store, _to_iso_date


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "")).strip().lower()



class RecheckService:

    MAX_CONSECUTIVE_FAILURES = 3

    # Fields we'll diff + update on a healthy recheck. Deliberately
    # excludes `title` - title is the identity we match extraction
    # results back against, not something we want silently rewritten.
    DIFF_FIELDS = (
        "organization",
        "scheme_type",
        "application_start",
        "application_end",
        "guidelines_url",
        "faq_url",
        "application_url",
        "scholarship_amount",
        "education_level",
        "income_criteria",
        "gender_criteria",
        "category_criteria",
        "domicile",
    )

    DATE_FIELDS = {"application_start", "application_end"}

    def _compute_status(self, end_date_str: Optional[str]) -> str:
        if not end_date_str:
            return 'ACTIVE'
        from datetime import date
        try:
            end_date = date.fromisoformat(end_date_str)
            today = date.today()
            delta = (end_date - today).days
            if delta < 0:
                return 'EXPIRED'
            elif delta <= 7:
                return 'EXPIRING_SOON'
        except Exception:
            pass
        return 'ACTIVE'

    def __init__(self, store):

        self.store = store

        self.page_crawler = PageCrawler(link_extractor=LinkExtractor())
        self.extractor = ScholarshipExtractor()

    # ======================================================
    # PUBLIC ENTRYPOINT
    # ======================================================

    def run(
        self,
        batch_size: int = 50,
        stale_after_hours: int = 24,
        only_active: bool = True,
    ) -> Dict[str, Any]:

        # Written up front (status=RUNNING) and closed out at the end
        # (status=COMPLETED/FAILED) in recheck_runs - this is what a
        # dashboard's "last updated on" should read, since it reflects
        # actual completed work rather than just a cron tick firing.
        # See database/supabase.py's start_recheck_run/finish_recheck_run
        # and recheck_runs_migration.sql.
        run_id = self.store.start_recheck_run(
            batch_size=batch_size,
            stale_after_hours=stale_after_hours,
            include_inactive=not only_active,
        )

        summary: Dict[str, Any] = {
            "recheck_run_id": run_id,
            "checked": 0,
            "still_active": 0,
            "reactivated": 0,
            "marked_inactive": 0,
            "fetch_failed": 0,
            "fields_updated": 0,
            "errors": 0,
            "started_at": _now_iso(),
        }

        run_status = "COMPLETED"

        try:

            due = self.store.get_scholarships_due_for_recheck(
                stale_after_hours=stale_after_hours,
                only_active=only_active,
                limit=batch_size,
            )

            print(f"[RecheckService] {len(due)} scholarship(s) due for recheck.")

            for scholarship in due:

                try:
                    outcome = self._recheck_one(scholarship)

                except Exception as exc:

                    print(
                        f"[RecheckService] Unexpected error rechecking "
                        f"scholarship id={scholarship.get('id')}: {exc}"
                    )

                    summary["errors"] += 1
                    continue

                summary["checked"] += 1

                if outcome["fetch_ok"]:
                    summary["still_active"] += 1
                else:
                    summary["fetch_failed"] += 1

                if outcome["reactivated"]:
                    summary["reactivated"] += 1

                if outcome["marked_inactive"]:
                    summary["marked_inactive"] += 1

                summary["fields_updated"] += outcome["fields_changed"]

        except Exception as exc:

            # Something broke outside the per-scholarship try/except
            # above (e.g. get_scholarships_due_for_recheck itself
            # failed) - the whole run is FAILED, not just one item.
            print(f"[RecheckService] Recheck run failed: {exc}")
            run_status = "FAILED"

        summary["finished_at"] = _now_iso()

        self.store.finish_recheck_run(run_id, summary, status=run_status)

        print(f"[RecheckService] Done: {summary}")

        return summary

    # ======================================================
    # PER-SCHOLARSHIP RECHECK
    # ======================================================

    def _recheck_one(self, scholarship: dict) -> Dict[str, Any]:

        scholarship_id = scholarship["id"]
        source_url = (scholarship.get("source_url") or "").strip()
        title = scholarship.get("title") or ""
        was_active = bool(scholarship.get("is_active", True))
        prior_failures = scholarship.get("consecutive_failures", 0) or 0

        print(
            f"[RecheckService] Rechecking id={scholarship_id}: "
            f"{title!r} ({source_url})"
        )

        page = self.page_crawler.crawl(source_url) if source_url else None

        page_ok = page is not None

        title_still_present = (
            page_ok
            and _normalize_text(title) in _normalize_text(page.get("text", ""))
        )

        healthy = page_ok and title_still_present

        if not healthy:
            return self._handle_unhealthy(
                scholarship_id=scholarship_id,
                was_active=was_active,
                prior_failures=prior_failures,
                page_ok=page_ok,
            )

        return self._handle_healthy(scholarship, page, was_active)

    # ------------------------------------------------------
    # UNHEALTHY: fetch failed, OR page loaded but the title vanished
    # ------------------------------------------------------

    def _handle_unhealthy(
        self,
        scholarship_id: int,
        was_active: bool,
        prior_failures: int,
        page_ok: bool,
    ) -> Dict[str, Any]:

        failures = prior_failures + 1

        reason = "unreachable" if not page_ok else "title no longer found on page"

        print(
            f"[RecheckService] id={scholarship_id} unhealthy ({reason}); "
            f"consecutive_failures {prior_failures} -> {failures}"
        )

        is_active_now = was_active and failures < self.MAX_CONSECUTIVE_FAILURES
        marked_inactive = was_active and not is_active_now

        field_updates = {}
        if marked_inactive:
            field_updates["computed_status"] = "NO_LONGER_VERIFIABLE"

        self.store.update_scholarship_after_recheck(
            scholarship_id,
            field_updates=field_updates,
            is_active=is_active_now,
            consecutive_failures=failures,
        )

        if marked_inactive:

            self.store.insert_scholarship_changes([{
                "scholarship_id": scholarship_id,
                "field_name": "is_active",
                "old_value": "true",
                "new_value": "false",
                "change_type": "MARKED_INACTIVE",
            }])

            print(
                f"[RecheckService] id={scholarship_id} MARKED INACTIVE "
                f"after {failures} consecutive failures."
            )

        return {
            "fetch_ok": False,
            "reactivated": False,
            "marked_inactive": marked_inactive,
            "fields_changed": 0,
        }

    # ------------------------------------------------------
    # HEALTHY: page reachable and title confirmed present
    # ------------------------------------------------------

    def _handle_healthy(
        self,
        scholarship: dict,
        page: dict,
        was_active: bool,
    ) -> Dict[str, Any]:

        scholarship_id = scholarship["id"]

        field_updates, field_changes = self._diff_fields(scholarship, page)

        reactivated = not was_active

        # Compute the status based on current application end date
        end_date = field_updates.get("application_end") or scholarship.get("application_end")
        new_status = self._compute_status(end_date)
        if new_status != scholarship.get("computed_status") or reactivated:
            field_updates["computed_status"] = new_status

        self.store.update_scholarship_after_recheck(
            scholarship_id,
            field_updates=field_updates,
            is_active=True,
            consecutive_failures=0,
        )

        change_rows = list(field_changes)

        if reactivated:

            change_rows.append({
                "scholarship_id": scholarship_id,
                "field_name": "is_active",
                "old_value": "false",
                "new_value": "true",
                "change_type": "REACTIVATED",
            })

            print(f"[RecheckService] id={scholarship_id} REACTIVATED.")

        if change_rows:
            self.store.insert_scholarship_changes(change_rows)

        if field_updates:
            print(
                f"[RecheckService] id={scholarship_id} updated fields: "
                f"{list(field_updates.keys())}"
            )

        return {
            "fetch_ok": True,
            "reactivated": reactivated,
            "marked_inactive": False,
            "fields_changed": len(field_updates),
        }

    # ------------------------------------------------------
    # FIELD DIFFING
    # ------------------------------------------------------

    def _diff_fields(
        self,
        scholarship: dict,
        page: dict,
    ) -> Tuple[Dict[str, Any], List[dict]]:
        """
        Re-extracts the page deterministically, matches the result back
        to THIS scholarship by normalized title, and diffs field-by-field
        against what's currently stored.

        A field the re-extraction didn't find (None) is treated as
        "we don't know" and left untouched - NOT as "this is now empty".
        Only changed, non-null new values are ever written.
        """

        extracted = self.extractor.extract(page, use_llm_fallback=False)

        match = self._match_extraction(scholarship.get("title", ""), extracted)

        if not match:
            return {}, []

        field_updates: Dict[str, Any] = {}
        changes: List[dict] = []

        for field in self.DIFF_FIELDS:

            new_normalized = self._normalize_field(field, match.get(field))

            if new_normalized is None:
                continue

            old_normalized = self._normalize_field(field, scholarship.get(field))

            if new_normalized == old_normalized:
                continue

            field_updates[field] = new_normalized

            changes.append({
                "scholarship_id": scholarship["id"],
                "field_name": field,
                "old_value": old_normalized,
                "new_value": new_normalized,
                "change_type": "FIELD_UPDATED",
            })

        return field_updates, changes

    def _normalize_field(self, field: str, value: Any) -> Optional[str]:

        if value is None:
            return None

        if field in self.DATE_FIELDS:
            # Reuses the exact same DD-MM-YYYY / ISO parsing supabase.py
            # already uses on insert, so "changed?" comparisons can't
            # false-positive on formatting differences alone.
            return _to_iso_date(value)

        value = str(value).strip()

        return value or None

    @staticmethod
    def _match_extraction(title: str, extracted: List[dict]) -> Optional[dict]:

        target = _normalize_text(title)

        if not target:
            return None

        # Exact match first.
        for item in extracted:
            if _normalize_text(item.get("title", "")) == target:
                return item

        # Fall back to a loose containment match - minor formatting
        # drift (extra whitespace, a trailing year, etc.) shouldn't
        # cost us a real match.
        for item in extracted:
            candidate = _normalize_text(item.get("title", ""))
            if candidate and (candidate in target or target in candidate):
                return item

        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ==================================================
# CLI ENTRYPOINT
# ==================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Recheck previously-discovered scholarships for liveness "
            "and field drift."
        )
    )

    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--stale-after-hours", type=int, default=24)
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Also attempt to recheck currently-inactive scholarships (looking for REACTIVATED).",
    )
    parser.add_argument("--skip-db", action="store_true")

    args = parser.parse_args()

    store = get_store(skip_db=args.skip_db)

    service = RecheckService(store)

    summary = service.run(
        batch_size=args.batch_size,
        stale_after_hours=args.stale_after_hours,
        only_active=not args.include_inactive,
    )

    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()