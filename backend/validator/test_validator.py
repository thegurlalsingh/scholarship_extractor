import json

from crawler.link_extractor import LinkExtractor
from crawler.page_crawler import PageCrawler
from crawler.portal_crawler import PortalCrawler

from validator.scholarship_validator import (
    ScholarshipValidator
)


START_URL = (
    "https://scholarships.gov.in/All-Scholarships"
)


def main():

    print("=" * 100)
    print("SCHOLARSHIP VALIDATOR TEST")
    print("=" * 100)

    # ------------------------------------------------------
    # CRAWLER
    # ------------------------------------------------------

    link_extractor = LinkExtractor()

    page_crawler = PageCrawler(
        link_extractor
    )

    portal_crawler = PortalCrawler(
        page_crawler,
        max_depth=2,
        max_pages=10
    )

    # ------------------------------------------------------
    # CRAWL
    # ------------------------------------------------------

    portal_crawler.crawl(
        START_URL
    )

    scholarships = (
        portal_crawler
        .get_potential_scholarships()
    )

    print(
        f"\nFound {len(scholarships)} "
        "potential scholarships."
    )

    # ------------------------------------------------------
    # VALIDATOR
    # ------------------------------------------------------

    validator = ScholarshipValidator()

    validated = validator.validate_many(
        scholarships
    )

    # ------------------------------------------------------
    # SAVE
    # ------------------------------------------------------

    validator.save_json(
        validated,
        "validated_scholarships.json"
    )

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

    print("\n")
    print("=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)

    for index, result in enumerate(
        validated,
        start=1
    ):

        scholarship = result[
            "scholarship"
        ]

        validation = result[
            "validation"
        ]

        print(
            f"\n{index}. "
            f"{scholarship.get('title')}"
        )

        print(
            "   Score      :",
            validation[
                "legitimacy_score"
            ]
        )

        print(
            "   Confidence :",
            validation[
                "confidence"
            ]
        )

        print(
            "   Status     :",
            validation[
                "status"
            ]
        )

    print("\n")
    print(
        "JSON saved as:"
        " validated_scholarships.json"
    )


if __name__ == "__main__":
    main()