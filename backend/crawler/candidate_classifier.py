# This has deterministic rules for Scholarships, Portal, Aggregators and Irrelevant links we get during crawling a website

from urllib.parse import urlparse


class CandidateClassifier:
    """
    Rule-based classifier for crawled pages.

    Possible classifications:
        SCHOLARSHIP
        PORTAL
        AGGREGATOR
        IRRELEVANT
    """

    SCHOLARSHIP_KEYWORDS = (
        "scholarship",
        "scholarships",
        "fellowship",
        "fellowships",
        "financial-aid",
        "financial_aid",
        "student-grant",
        "education-grant",
    )

    PORTAL_KEYWORDS = (
        "portal",
        "student",
        "students",
        "apply",
        "application",
        "applications",
        "scheme",
        "schemes",
        "search",
        "listing",
        "all-scholarships",
    )

    IRRELEVANT_KEYWORDS = (
        "login",
        "signin",
        "sign-in",
        "signup",
        "sign-up",
        "register",
        "contact",
        "privacy",
        "terms",
        "career",
        "careers",
        "admin",
        "dashboard",
        "facebook",
        "instagram",
        "twitter",
        "youtube",
        "linkedin",
    )

    KNOWN_AGGREGATORS = (
        "buddy4study.com",
        "vidyasaarathi.co.in",
        "scholarships.com",
        "scholars4dev.com",
        "scholarshipportal.com",
    )

    KNOWN_PORTALS = (
        "scholarships.gov.in",
        "scholarship.up.gov.in",
        "pmsonline.bihar.gov.in",
        "myscheme.gov.in",
    )

    def classify(
        self,
        url: str,
        title: str = "",
        text: str = "",
    ) -> str:

        domain = self._extract_domain(url)

        path = self._extract_path(url)

        combined = (
            f"{url} "
            f"{title} "
            f"{text[:3000]}"
        ).lower()


        if domain in self.KNOWN_AGGREGATORS:
            return "AGGREGATOR"


        if domain in self.KNOWN_PORTALS:
            return "PORTAL"

        # --------------------------------------------------
        # 3. IRRELEVANT PAGES
        # --------------------------------------------------

        if any(
            keyword in path
            for keyword in self.IRRELEVANT_KEYWORDS
        ):
            return "IRRELEVANT"

        # --------------------------------------------------
        # 4. STRONG SCHOLARSHIP SIGNAL
        # --------------------------------------------------

        scholarship_score = sum(
            1
            for keyword in self.SCHOLARSHIP_KEYWORDS
            if keyword in combined
        )

        # A page containing multiple scholarship signals
        # is likely an actual scholarship page.
        if scholarship_score >= 2:
            return "SCHOLARSHIP"

        # --------------------------------------------------
        # 5. PORTAL SIGNALS
        # --------------------------------------------------

        portal_score = sum(
            1
            for keyword in self.PORTAL_KEYWORDS
            if keyword in path
        )

        if portal_score >= 2:
            return "PORTAL"

        # --------------------------------------------------
        # 6. SINGLE SCHOLARSHIP SIGNAL
        # --------------------------------------------------

        if scholarship_score == 1:

            # Look for actual scholarship information.
            info_keywords = (
                "eligibility",
                "amount",
                "benefit",
                "deadline",
                "last date",
                "apply now",
                "selection",
                "documents",
            )

            info_score = sum(
                1
                for keyword in info_keywords
                if keyword in combined
            )

            if info_score >= 2:
                return "SCHOLARSHIP"

        # --------------------------------------------------
        # 7. DEFAULT
        # --------------------------------------------------

        return "IRRELEVANT"

    @staticmethod
    def _extract_domain(url: str) -> str:

        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        # Remove port
        domain = domain.split(":")[0]

        return domain

    @staticmethod
    def _extract_path(url: str) -> str:

        return urlparse(url).path.lower()