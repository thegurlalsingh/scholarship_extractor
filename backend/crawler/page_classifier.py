"""
Classifies the type of a crawled page.

Determines if a page is a normal content page, a portal dashboard, a scholarship 
listing page (containing multiple schemes), or a scholarship detail page. This 
classification drives the crawler's decision on whether to extract scholarships 
and whether to follow internal links.
"""

import re


class PageClassifier:

    NORMAL_PAGE = "NORMAL_PAGE"
    PORTAL_PAGE = "PORTAL_PAGE"
    SCHOLARSHIP_LISTING = "SCHOLARSHIP_LISTING"
    SCHOLARSHIP_DETAIL = "SCHOLARSHIP_DETAIL"


    # Strong listing signals


    LISTING_SIGNALS = (
        "schemes on nsp",
        "central sector scheme",
        "centrally sponsored scheme",
        "state scheme",
        "select scheme",
        "select state",
        "scheme open from",
        "student application open till",
        "defective application verification",
        "institute verification",
        "dno/sno/mno verification",
        "merit based scheme",
        "welfare based scheme",
    )


    # Individual scholarship signals


    DETAIL_SIGNALS = (
        "eligibility",
        "scholarship amount",
        "scholarship benefits",
        "application process",
        "documents required",
        "selection process",
        "terms and conditions",
    )


    # Portal signals


    PORTAL_SIGNALS = (
        "login",
        "dashboard",
        "one time registration",
        "student login",
        "institute login",
        "application status",
        "track application",
    )

    def classify(self, page: dict) -> str:

        title = (page.get("title") or "").lower()
        text = (page.get("text") or "").lower()
        url = (page.get("url") or "").lower()

        content = f"{title} {text} {url}"

        # Source HTML has inconsistent inline whitespace (e.g.
        # "Scheme  Open from" with a double space), which breaks
        # plain substring matches against our single-spaced signal
        # phrases below. Collapse all whitespace runs to one space.
        content = re.sub(r"\s+", " ", content)


        # 1. URL-BASED LISTING DETECTION

        #
        # This is important.
        #
        # If the URL itself is:
        #
        # /All-Scholarships
        #
        # we KNOW this is intended to be the scholarship
        # listing page.
        #

        listing_url_patterns = (
            "/all-scholarships",
            "/all-scholarship",
            "/scholarships",
            "/scholarship-list",
            "/scholarship-listing",
            "/schemes",
        )

        if any(
            pattern in url
            for pattern in listing_url_patterns
        ):
            return self.SCHOLARSHIP_LISTING


        # 2. LISTING CONTENT DETECTION


        listing_score = self._count_signals(
            content,
            self.LISTING_SIGNALS
        )

        # A page with several of these signals is almost
        # certainly a scholarship listing page.

        if listing_score >= 3:
            return self.SCHOLARSHIP_LISTING


        # 3. SCHOLARSHIP DETAIL


        detail_score = self._count_signals(
            content,
            self.DETAIL_SIGNALS
        )

        scholarship_words = self._count_words(
            content,
            (
                "scholarship",
                "scheme",
                "fellowship",
            )
        )

        if (
            detail_score >= 2
            and scholarship_words >= 1
        ):
            return self.SCHOLARSHIP_DETAIL


        # 4. PORTAL


        portal_score = self._count_signals(
            content,
            self.PORTAL_SIGNALS
        )

        if portal_score >= 2:
            return self.PORTAL_PAGE


        # 5. NORMAL


        return self.NORMAL_PAGE

    # ======================================================
    # HELPERS
    # ======================================================

    @staticmethod
    def _count_signals(
        content: str,
        signals: tuple
    ) -> int:

        return sum(
            1
            for signal in signals
            if signal in content
        )

    @staticmethod
    def _count_words(
        content: str,
        words: tuple
    ) -> int:

        return sum(
            len(
                re.findall(
                    rf"\b{re.escape(word)}\b",
                    content
                )
            )
            for word in words
        )