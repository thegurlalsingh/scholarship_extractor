# Defines what a discovered candidate looks like.
# At this stage it's not yet a verified scholarship.

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScholarshipCandidate:
    title: str
    url: str
    snippet: Optional[str] = None
    discovery_query: Optional[str] = None
    discovered_from: Optional[str] = None
    
    source_type: Optional[str] = None # Type of source/domain -> GOVERNMENT, UNIVERSITY, CORPORATE, FOUNDATION, AGGREGATOR, OTHER
    domain: Optional[str] = None
    candidate_type: Optional[str] = None # What the actual discovered page represents -> SCHOLARSHIP, PORTAL, AGGREGATOR, IRRELEVANT, UNKNOWN
    
    is_official_source: Optional[bool] = None # This must NOT be guessed during discovery. Verification will determine this later.