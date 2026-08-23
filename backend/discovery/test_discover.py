from discovery.discovery_engine import DiscoveryEngine
from discovery.search_provider import BingSearchProvider
from discovery.source_classifier import SourceClassifier
from discovery.candidate_classifier import CandidateClassifier

def main():

    search_provider = BingSearchProvider(
        max_results=5,
        region="in-en",
    )

    source_classifier = SourceClassifier()

    candidate_classifier = CandidateClassifier()

    engine = DiscoveryEngine(
        search_provider=search_provider,
        source_classifier=source_classifier,
        candidate_classifier=candidate_classifier
    )

    candidates = engine.discover()

    print("\n")
    print("=" * 100)
    print("SCHOLARSHIP DISCOVERY RESULTS")
    print("=" * 100)

    print(f"\nTotal candidates discovered: {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):

        print("\n" + "-" * 100)

        print(f"Candidate #{index}")
        print(f"Title        : {candidate.title}")
        print(f"URL          : {candidate.url}")
        print(f"Domain       : {candidate.domain}")
        print(f"Source Type  : {candidate.source_type}")
        print(f"Likely Official: {candidate.is_official_source}")
        print(f"Search Query : {candidate.discovery_query}")
        print(f"Snippet      : {candidate.snippet}")
        print(f"Candidate Type: {candidate.candidate_type}")
        print(f"Official Source: {candidate.is_official_source}")

    print("\n" + "=" * 100)
    print("DISCOVERY COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()