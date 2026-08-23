# Actually performs the web search.
# query -> Search provider -> URLs + titles + snippets
# Keep this separate because later we can change the search mechanism without touching the discovery logic.

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ddgs import DDGS


class SearchProvider(ABC):

    @abstractmethod
    def search(self, query: str) -> List[Dict[str, Any]]:
        raise NotImplementedError


class WebSearchProvider(SearchProvider):
    """
    NOTE: this used to be called BingSearchProvider and pass
    backend="bing". As of the current `ddgs` package, "bing" is NOT
    a registered backend for text search (only brave, duckduckgo,
    grokipedia, mojeek, startpage, wikipedia, yahoo are). Passing an
    unregistered backend does not raise an error - ddgs silently
    falls back to "auto", which also mixes in wikipedia/grokipedia
    (encyclopedia lookups, not web search - useless for
    site:gov.in-style queries and can crowd out real results).

    We explicitly list real web-search engines here instead of
    relying on the "auto"/"bing" fallback.
    """

    def __init__(
        self,
        max_results: int = 10,
        region: str = "in-en",
        safesearch: str = "moderate",
        timeout: int = 10,
        backend: str = "duckduckgo,brave,startpage,mojeek,yahoo",
    ):
        self.max_results = max_results
        self.region = region
        self.safesearch = safesearch
        self.timeout = timeout
        self.backend = backend

        self.client = DDGS(
            timeout=timeout
        )

    def search(self, query: str) -> List[Dict[str, Any]]:

        if not query or not query.strip():
            return []

        try:

            raw_results = self.client.text(
                query=query,
                region=self.region,
                safesearch=self.safesearch,
                backend=self.backend,
                max_results=self.max_results,
            )

            results = []

            for item in raw_results:

                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                    }
                )

            print(
                f"[WebSearchProvider] "
                f"'{query}' → {len(results)} results"
            )

            return results

        except Exception as exc:

            print(
                f"[WebSearchProvider] "
                f"Search failed for '{query}'"
            )

            print(f"Reason: {exc}")

            return []


# Backwards-compatible alias so existing imports don't break.
BingSearchProvider = WebSearchProvider