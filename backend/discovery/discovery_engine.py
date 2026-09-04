"""
Orchestrates the entire candidate discovery phase.

Runs every configured search strategy, deduplicates results by URL, classifies
each URL by source type (government, university, corporate, etc.), and returns a
flat list of ScholarshipCandidate objects ready for crawling.
"""

from typing import List, Set

from .candidate import ScholarshipCandidate
from .strategies import DISCOVERY_STRATEGIES
from .source_classifier import SourceClassifier
from .candidate_classifier import CandidateClassifier
from .search_provider import SearchProvider


class DiscoveryEngine:

    def __init__(
        self,
        search_provider: SearchProvider,
        source_classifier: SourceClassifier,
        candidate_classifier: CandidateClassifier,
    ):
        self.search_provider = search_provider
        self.source_classifier = source_classifier
        self.candidate_classifier = candidate_classifier

    def discover(self) -> List[ScholarshipCandidate]:
        import time

        candidates: List[ScholarshipCandidate] = []
        seen_urls: Set[str] = set()

        for strategy in DISCOVERY_STRATEGIES:
            for query in strategy.queries:
                results = self.search_provider.search(query)
                time.sleep(1.0)  # Rate limit pause for web search engine

                for result in results:
                    url = result.get("url")
                    if not url:
                        continue

                    normalized_url = self._normalize_url(url)
                    if normalized_url in seen_urls:
                        continue

                    seen_urls.add(normalized_url)

                    source_type = self.source_classifier.classify(normalized_url)
                    candidate_type = self.candidate_classifier.classify(
                        title=result.get("title", ""),
                        snippet=result.get("snippet"),
                        url=normalized_url,
                        source_type=source_type,
                    )

                    candidate = ScholarshipCandidate(
                        title=result.get("title", ""),
                        url=normalized_url,
                        snippet=result.get("snippet"),
                        discovery_query=query,
                        discovered_from="web_search",
                        source_type=source_type,
                        domain=self._extract_domain(normalized_url),
                        candidate_type=candidate_type,
                        is_official_source=None,
                    )

                    candidates.append(candidate)

        return candidates

    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.strip().rstrip("/")

    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain