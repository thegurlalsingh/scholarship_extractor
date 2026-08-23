# Determines what kind of organization/source owns the candidate URL.
#
# IMPORTANT:
# This classifier does NOT decide whether the page is an actual
# scholarship or a portal. That is handled separately.

from urllib.parse import urlparse


class SourceClassifier:

    GOVERNMENT_SUFFIXES = (
        ".gov.in",
        ".nic.in",
    )

    GOVERNMENT_DOMAINS = (
        "scholarships.gov.in",
        "education.gov.in",
        "ugc.gov.in",
        "aicte-india.org",
        "myscheme.gov.in",
        "india.gov.in",
        "socialjustice.gov.in",
        "tribal.nic.in",
        "minorityaffairs.gov.in",
        "depwd.gov.in",
        "dhe.gov.in",
    )

    UNIVERSITY_SUFFIXES = (
        ".ac.in",
        ".edu.in",
    )

    UNIVERSITY_KEYWORDS = (
        "university",
        "college",
        "institute",
        "iit",
        "nit",
        "iiit",
        "bits",
    )

    AGGREGATOR_DOMAINS = (
        "buddy4study.com",
        "vidyasaarathi.co.in",
        "indiascholarships.in",
        "scholarsanta.com",
        "scholarshipportal.com",
        "nspscholarship.org",
    )

    CORPORATE_DOMAINS = (
        "reliancefoundation.org",
        "sbi.co.in",
        "hdfcbank.com",
        "tatatrusts.org",
        "godrej.com",
    )

    CORPORATE_KEYWORDS = (
        "foundation",
        "corporate",
        "csr",
    )

    FOUNDATION_KEYWORDS = (
        "trust",
        "ngo",
        "charitable",
        "charity",
        "society",
    )

    def classify(self, url: str) -> str:

        domain = self._extract_domain(url)

        if domain in self.GOVERNMENT_DOMAINS:
            return "GOVERNMENT"

        if domain.endswith(self.GOVERNMENT_SUFFIXES):
            return "GOVERNMENT"

        if domain in self.AGGREGATOR_DOMAINS:
            return "AGGREGATOR"

        if domain.endswith(self.UNIVERSITY_SUFFIXES):
            return "UNIVERSITY"

        if any(
            keyword in domain
            for keyword in self.UNIVERSITY_KEYWORDS
        ):
            return "UNIVERSITY"

        if domain in self.CORPORATE_DOMAINS:
            return "CORPORATE"

        if any(
            keyword in domain
            for keyword in self.CORPORATE_KEYWORDS
        ):
            return "CORPORATE"

        if any(
            keyword in domain
            for keyword in self.FOUNDATION_KEYWORDS
        ):
            return "FOUNDATION"

        return "OTHER"

    @staticmethod
    def _extract_domain(url: str) -> str:

        parsed = urlparse(url)

        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain