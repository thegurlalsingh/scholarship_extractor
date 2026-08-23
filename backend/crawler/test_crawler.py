from .page_crawler import PageCrawler
from .link_extractor import LinkExtractor
from .portal_crawler import PortalCrawler


def main():

    page_crawler = PageCrawler(
        link_extractor=LinkExtractor()
    )

    portal_crawler = PortalCrawler(
        page_crawler=page_crawler,

        max_depth=2,
        max_pages=10,
    )

    start_url = "https://scholarships.gov.in/All-Scholarships"

    print("\n")
    print("=" * 100)
    print("PORTAL CRAWLER TEST")
    print("=" * 100)

    print(f"\nStarting URL: {start_url}")
    print(f"Max Depth: 2")
    print(f"Max Pages: 10")

    print("\n" + "-" * 100)

    pages = portal_crawler.crawl(start_url)

    scholarships = (
        portal_crawler.get_potential_scholarships()
    )

    print("\n")
    print("=" * 100)
    print("EXTRACTED SCHOLARSHIPS")
    print("=" * 100)

    print(
        f"\nTotal scholarships: "
        f"{len(scholarships)}"
    )

    for index, scholarship in enumerate(
        scholarships,
        start=1
    ):

        print("\n" + "-" * 100)

        print(
            f"SCHOLARSHIP #{index}"
        )

        print(
            f"Title              : "
            f"{scholarship.get('title')}"
        )

        print(
            f"Organization        : "
            f"{scholarship.get('organization')}"
        )

        print(
            f"Scheme Type         : "
            f"{scholarship.get('scheme_type')}"
        )

        print(
            f"Application Start   : "
            f"{scholarship.get('application_start')}"
        )

        print(
            f"Application End     : "
            f"{scholarship.get('application_end')}"
        )

        print(
            f"Guidelines URL      : "
            f"{scholarship.get('guidelines_url')}"
        )

        print(
            f"FAQ URL             : "
            f"{scholarship.get('faq_url')}"
        )

    print("\n")
    print("=" * 100)
    print("CRAWL COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()