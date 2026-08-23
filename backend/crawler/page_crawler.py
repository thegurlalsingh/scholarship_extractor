"""
Given a URL, fetches the page and returns clean page content.

Includes a legacy SSL adapter to bypass 'unsafe legacy renegotiation disabled' 
errors common on older Indian government servers, ensuring these domains aren't 
silently dropped during crawls.
"""

import ssl
import time
import requests
from requests.adapters import HTTPAdapter

class _LegacySSLAdapter(HTTPAdapter):

    def init_poolmanager(self, *args, **kwargs):

        context = ssl.create_default_context()

        # OP_LEGACY_SERVER_CONNECT isn't exposed as a named constant on
        # every Python build, so fall back to the raw flag value (0x4)
        # if needed.
        legacy_flag = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        context.options |= legacy_flag

        kwargs["ssl_context"] = context

        return super().init_poolmanager(*args, **kwargs)


class PageCrawler:

    def __init__(self, link_extractor):

        self.link_extractor = link_extractor

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            )
        })

        # Lazily created only if/when we actually hit a legacy-SSL server.
        self._legacy_session = None

    def _get_legacy_session(self):

        if self._legacy_session is None:

            legacy_session = requests.Session()
            legacy_session.headers.update(self.session.headers)

            adapter = _LegacySSLAdapter()
            legacy_session.mount("https://", adapter)

            self._legacy_session = legacy_session

        return self._legacy_session

    def crawl(self, url: str):

        for attempt in range(3):

            try:

                response = self.session.get(
                    url,
                    timeout=(10, 30),
                    allow_redirects=True
                )

                response.raise_for_status()

                return self._build_result(response)

            except requests.exceptions.SSLError as e:

                print(
                    f"[PageCrawler] SSL error on attempt "
                    f"{attempt + 1}/3, retrying with legacy-SSL adapter: {url}"
                )
                print(f"[PageCrawler] Error: {e}")

                try:

                    legacy_session = self._get_legacy_session()

                    response = legacy_session.get(
                        url,
                        timeout=(10, 30),
                        allow_redirects=True
                    )

                    response.raise_for_status()

                    print(
                        f"[PageCrawler] Legacy-SSL retry succeeded: {url}"
                    )

                    return self._build_result(response)

                except requests.RequestException as legacy_error:

                    print(
                        f"[PageCrawler] Legacy-SSL retry also failed: "
                        f"{legacy_error}"
                    )

                    if attempt < 2:
                        time.sleep(2)

            except requests.RequestException as e:

                print(
                    f"[PageCrawler] Attempt "
                    f"{attempt + 1}/3 failed: {url}"
                )

                print(
                    f"[PageCrawler] Error: {e}"
                )

                if attempt < 2:
                    time.sleep(2)

        print(
            f"[PageCrawler] Giving up: {url}"
        )

        return None

    def _build_result(self, response):

        links = self.link_extractor.extract(
            response.text,
            response.url
        )

        print(
            f"[PageCrawler] Extracted "
            f"{len(links)} links"
        )

        return {
            "url": response.url,
            "title": self._extract_title(response.text),
            "status": response.status_code,
            "text": self._extract_text(response.text),
            "links": links,
            "html": response.text
        }

    @staticmethod
    def _extract_title(html: str) -> str:

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        if soup.title:
            return soup.title.get_text(
                strip=True
            )

        return ""

    @staticmethod
    def _extract_text(html: str) -> str:

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Remove things that aren't useful
        # for scholarship extraction.
        for tag in soup([
            "script",
            "style",
            "noscript"
        ]):
            tag.decompose()

        return soup.get_text(
            " ",
            strip=True
        )