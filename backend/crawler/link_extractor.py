# Its only job: Take crawled HTML → extract and clean links. It does not decide whether a link is a scholarship or portal. That comes later.

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List


class LinkExtractor:

    def extract(
        self,
        html: str,
        base_url: str,
    ) -> List[str]:

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        links = set()

        for tag in soup.find_all("a", href=True):

            href = tag.get("href", "").strip()

            if not href:
                continue

            absolute_url = urljoin(
                base_url,
                href
            )

            parsed = urlparse(absolute_url)

            if parsed.scheme not in {
                "http",
                "https"
            }:
                continue

            clean_url = absolute_url.split("#")[0]

            if not clean_url:
                continue

            links.add(clean_url.rstrip("/"))

        return list(links)