# Determines what the discovered page represents.
# This is intentionally a deterministic first version.
# Later we can replace/enhance this with an LLM/page-content classifier.

import re
from typing import Optional


class CandidateClassifier:

    # Signals that a page is a DIRECTORY/LISTING of many scholarships,
    # not a page about one specific scholarship. Kept deliberately
    # narrower than SCHOLARSHIP_KEYWORDS - avoid phrases like
    # "scholarship scheme" / "scholarship schemes" here, since that's
    # literally how many individual Indian scholarships are named
    # (e.g. "AICTE Pragati Scholarship Scheme"). A phrase that matches
    # both a real scholarship's own name and "this is a directory" is
    # not a useful portal signal.
    PORTAL_KEYWORDS = (
        "scholarship portal",
        "scholarships portal",
        "scholarship applications",
        "online scholarship",
        "scholarships for students",
        "find scholarships",
        "list of scholarships",
        "all scholarships",
        "browse scholarships",
        "scholarships in india",
        "latest scholarships",
        "scholarship database",
        "compare scholarships",
    )

    AGGREGATOR_DOMAINS = (
        "buddy4study.com",
        "indiascholarships.in",
        "scholarsanta.com",
        "scholarshipportal.com",
        "nspscholarship.org",
        "vidyasaarathi.co.in",
    )

    SCHOLARSHIP_KEYWORDS = (
        "scholarship",
        "fellowship",
        "grant",
        "financial aid",
        "education assistance",
        "student award",
    )

    IRRELEVANT_KEYWORDS = (
        "admission",
        "counselling",
        "entrance exam",
        "results",
        "course",
        "college admissions",
        "registration",
    )

    # Matches "scholarship 2026", "scholarship 2026-27", "scholarship
    # 2026–27" etc. without hardcoding a specific year, so this keeps
    # working in future years without a code change.
    _YEAR_SCHOLARSHIP_RE = re.compile(
        r"\b(scholarship|fellowship)\b\s*20\d{2}(\s*[-–]\s*\d{2,4})?"
    )

    _SPECIFIC_SCHOLARSHIP_PHRASES = (
        "scholarship application",
        "apply for scholarship",
        "scholarship program",
        "scholarship programme",
        "education grant",
        "last date to apply",
        "eligibility criteria",
    )

    def classify(
        self,
        title: str,
        snippet: Optional[str],
        url: str,
        source_type: Optional[str] = None,
    ) -> str:

        title = (title or "").lower()
        snippet = (snippet or "").lower()
        url = (url or "").lower()

        text = f"{title} {snippet}"

        if self._is_aggregator_domain(url):
            return "AGGREGATOR"

        # --------------------------------------------------
        # IRRELEVANT: check this before anything else. A result
        # about admissions/counselling/exam-results that merely
        # mentions "scholarship" in passing shouldn't get any
        # further classification.
        # --------------------------------------------------

        irrelevant_score = sum(
            1
            for keyword in self.IRRELEVANT_KEYWORDS
            if keyword in text
        )

        scholarship_score = sum(
            1
            for keyword in self.SCHOLARSHIP_KEYWORDS
            if keyword in text
        )

        if irrelevant_score > 0 and scholarship_score == 0:
            return "IRRELEVANT"

        if scholarship_score == 0:
            return "IRRELEVANT"

        # --------------------------------------------------
        # SCHOLARSHIP vs PORTAL: score both, let the stronger
        # signal win instead of an early "first match" return.
        # This stops named scholarships like "... Scholarship
        # Scheme" from being misfiled as PORTAL.
        # --------------------------------------------------

        portal_score = sum(
            1
            for keyword in self.PORTAL_KEYWORDS
            if keyword in text
        )

        specific_score = sum(
            1
            for phrase in self._SPECIFIC_SCHOLARSHIP_PHRASES
            if phrase in text
        )

        if self._YEAR_SCHOLARSHIP_RE.search(text):
            specific_score += 1

        # No positive evidence this is a directory/listing page ->
        # default to SCHOLARSHIP. We already know scholarship_score
        # > 0 at this point (checked above), so absence of a portal
        # signal is the more informative case here.
        if portal_score == 0:
            return "SCHOLARSHIP"

        if specific_score > portal_score:
            return "SCHOLARSHIP"

        return "PORTAL"

    def _is_aggregator_domain(self, url: str) -> bool:

        for domain in self.AGGREGATOR_DOMAINS:

            if domain in url:
                return True

        return False