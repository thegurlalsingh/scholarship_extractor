Scholarship Intelligence Crawler — PRD
1. Product Overview

Build an automated Scholarship Intelligence Crawler for Indian students that continuously discovers, crawls, extracts, verifies, scores, stores, and updates authentic scholarship opportunities from the internet.

The system must prioritize accuracy and traceability over quantity.

The final system should maintain a continuously updated scholarship repository where every important piece of information can be traced back to an official/primary source and supporting evidence.

2. Objective

The system should perform the following lifecycle:

DISCOVER
   ↓
CLASSIFY SOURCE
   ↓
CRAWL
   ↓
EXTRACT
   ↓
NORMALIZE
   ↓
VERIFY
   ↓
SCORE
   ↓
STORE
   ↓
MONITOR
   ↓
DETECT CHANGES
   ↓
UPDATE

The system should support both:

New scholarship discovery
Monitoring and re-verification of existing scholarships
3. Scope

The system will focus on scholarships/funding opportunities available to Indian students.

Potential sources include:

Government scholarship portals
Central Government departments
State Government departments
UGC
AICTE
Government ministries
Universities
Colleges
Corporate CSR programmes
Foundations
Trusts
NGOs
International organisations
Other legitimate scholarship providers
4. Core Functional Requirements
4.1 Scholarship Discovery

The system must discover scholarship opportunities beyond a completely hard-coded list of URLs.

Discovery process
Search / Seed Sources
        ↓
Candidate URLs
        ↓
Candidate Scholarship
        ↓
Source Classification

Discovery may use:

Search engines
Scholarship portals
Government directories
University websites
Foundation websites
Corporate CSR pages
Other legitimate discovery sources

Aggregators and blogs may be used for discovery only.

They must not become the authoritative source.

Output

Each discovered candidate should contain:

Candidate name
Candidate URL
Discovery source
Discovery timestamp
Potential provider
Potential source type
5. Source Classification

Every discovered source should be classified.

Possible source types:

GOVERNMENT
UNIVERSITY
CORPORATE
FOUNDATION
TRUST
NGO
INTERNATIONAL
SCHOLARSHIP_PORTAL
AGGREGATOR
BLOG
OTHER

The system should determine whether the source is potentially an official/primary source.

Important rule
Aggregator
    ↓
Discovery only
    ↓
Find primary source
    ↓
Verify against primary source

An aggregator must never be treated as sufficient evidence for a VERIFIED scholarship.

6. Crawling

The crawler should retrieve scholarship information from discovered sources.

It should support:

Static HTML pages
JavaScript-rendered pages where required
Relevant internal scholarship pages
Application pages
Official notifications/documents where necessary

For every crawl, record:

URL
Crawl timestamp
HTTP/result status
Retrieved content
Source domain
Content hash
Crawl success/failure
7. Scholarship Extraction

The system should convert unstructured website information into a normalized scholarship structure.

Minimum fields:

Scholarship Name
Provider
Official Source URL
Application URL
Source Type
Scholarship Amount / Benefit
Eligibility
Academic Requirements
Education Level
Course Requirements
Income Criteria
Age Criteria
Gender Criteria
Category Criteria
Domicile / State Requirements
Institution Requirements
Opening Date
Closing Date
Documents Required
Selection Process
Renewal Requirements
Current Status

Additional fields may be added where useful.

8. Evidence-Based Extraction

Every important extracted field should ideally have supporting evidence.

Example:

Field:
deadline

Value:
31 August 2026

Evidence:
"The last date for submitting applications is
31 August 2026."

Source:
Official scholarship page

The system should store:

Field name
Extracted value
Evidence text
Source URL
Evidence timestamp

If a field is not mentioned by the source:

Income Criteria: Not specified

The system must never infer or fabricate missing information.

9. Normalization

Extracted information should be converted into a consistent schema.

Examples:

₹50,000
₹50K
INR 50,000
Rs. 50,000

should be normalized into a consistent representation.

Dates should use a consistent format.

Education levels should use normalized values such as:

SCHOOL
UG
PG
PHD
DIPLOMA
RESEARCH
OTHER

Eligibility conditions should be represented in a structured manner where possible.

10. Verification Engine

The verification engine determines whether extracted scholarship information is supported by reliable evidence.

Verification should evaluate:

Source authenticity
Is the source official?
Is the provider identifiable?
Does the domain belong to the provider?
Is the scholarship actually present on the official source?
Information evidence
Is eligibility supported?
Is the scholarship amount supported?
Is the deadline supported?
Is the application URL supported?
Are important claims directly supported?
Freshness
Is the source currently accessible?
Is the information current?
Is the scholarship still accepting applications?
Has the deadline passed?
Conflicts

Check for:

Conflicting official pages
Conflicting deadlines
Different scholarship amounts
Outdated notifications
Contradictory eligibility information
11. Confidence Scoring

The system must calculate confidence using a deterministic evidence-based methodology.

The LLM must not simply generate the confidence score.

Example scoring dimensions:

Official source
Scholarship existence confirmed
Official application URL
Provider verified
Eligibility evidence
Amount evidence
Deadline evidence
Current/fresh source
No conflicting official information
Extraction consistency

The exact weighting should be defined during implementation.

Status rule
Confidence >= 95%
        ↓
VERIFIED

Confidence < 95%
        ↓
REVIEW_REQUIRED

The confidence score must be explainable.

Example:

Confidence: 97.8%

Reasons:
✓ Official government domain
✓ Scholarship found on official source
✓ Official application URL
✓ Eligibility directly supported
✓ Deadline directly supported
✓ Provider verified
✓ No conflicting official information
12. Anti-Hallucination Requirements

The system must never invent scholarship information.

Incorrect
Website does not mention income limit

LLM:
Income limit = ₹5 lakh
Correct
Income limit = Not specified

Every critical field should ideally have:

Value
+
Evidence
+
Source URL

The database should support:

Database
   ↓
Scholarship field
   ↓
Evidence
   ↓
Official source
13. Database

The system should maintain a persistent database.

Recommended logical entities:

Scholarships

Stores the latest/current scholarship state.

Evidence

Stores field-level source evidence.

Change History

Stores historical modifications.

Crawl Runs

Stores information about every crawler execution.

Sources

Stores discovered and classified sources.

14. Scholarship Lifecycle

Each scholarship should have a lifecycle.

DISCOVERED
    ↓
CRAWLED
    ↓
EXTRACTED
    ↓
VERIFIED / REVIEW_REQUIRED
    ↓
ACTIVE
    ↓
EXPIRING_SOON
    ↓
EXPIRED

Other possible states:

NO_LONGER_VERIFIABLE
15. Continuous Monitoring

The crawler must not operate as a one-time scraper.

Each scheduled run should perform two activities:

A. Discover new scholarships
Discovery
   ↓
New candidates
   ↓
Process
   ↓
Database
B. Monitor existing scholarships
Existing scholarships
        ↓
Revisit official source
        ↓
Compare with stored record
        ↓
Unchanged / Changed / Removed

Therefore:

NEW DISCOVERY
      +
EXISTING MONITORING
      ↓
UPDATED REPOSITORY
16. Change Detection

The system must detect changes between previous and current crawls.

Examples:

Deadline:
31 August → 15 September
Amount:
₹50,000 → ₹75,000
Eligibility:
UG students → UG + PG students

When a change occurs, store:

Scholarship ID
Field changed
Old value
New value
Detection timestamp
Source URL
New evidence

The old value must not be permanently lost.

17. Unchanged Records

If the official source has not changed:

OLD HASH == NEW HASH

or equivalent normalized comparison should indicate:

UNCHANGED

The system should avoid unnecessary re-processing where possible.

18. Stale / Expired Detection

The system should identify scholarships that are no longer current.

Expired

Deadline has passed.

Current date > closing date

→ EXPIRED

No longer verifiable

Official source is unavailable or the scholarship can no longer be confirmed.

→ NO_LONGER_VERIFIABLE

Review required

Important information cannot be confidently verified.

→ REVIEW_REQUIRED

Expiring soon

Deadline is approaching within a defined threshold.

→ EXPIRING_SOON

19. Scheduling

The system should support repeated execution.

The scheduler should trigger the crawler periodically.

Example conceptual flow:

Scheduler
    ↓
Crawler Run
    ↓
Discovery
    ↓
Existing Scholarship Monitoring
    ↓
Verification
    ↓
Change Detection
    ↓
Database Update

The system does not need to run every few minutes.

The objective is repeated automated execution, not keeping a web server artificially alive.

20. Incremental Crawling

The crawler should avoid unnecessarily processing every scholarship through the complete pipeline on every run.

Conceptually:

Existing source
      ↓
Check accessibility/content
      ↓
Compare hash / normalized content
      ↓
      ┌───────────────┐
      │               │
 UNCHANGED         CHANGED
      │               │
      ↓               ↓
    Skip       Extract + Verify
                      ↓
                 Change Detection
                      ↓
                    Update

Newly discovered scholarships should go through the full pipeline.

21. Dashboard

Build a simple interface showing the current state of the repository.

Dashboard metrics
Total discovered
Total verified
Review required
Active
Expired
Expiring soon
No longer verifiable
Recently updated
Average confidence
22. Scholarship Search

The dashboard should allow users to search/filter scholarships.

Possible filters:

Scholarship name
Provider
Source type
Education level
State/domicile
Category
Gender
Income criteria
Status
Confidence
Deadline
23. Scholarship Details

Opening a scholarship should display:

Name
Provider
Amount
Eligibility
Academic Requirements
Income Criteria
Category
Domicile
Education Level
Opening Date
Closing Date
Documents
Selection Process
Renewal Requirements
Official Source
Application URL
Status
Confidence Score

Also show:

Why this score?

and:

Source Evidence

and:

Change History
24. Crawl Run Monitoring

The system should maintain a record of each crawl execution.

Each run should capture:

Run ID
Start Time
End Time
Sources Discovered
Scholarships Discovered
New Scholarships
Updated Scholarships
Unchanged Scholarships
Expired Scholarships
Review Required
Errors

This allows the demo to clearly show what happened during each run.

25. Minimum Dataset Requirements

The final system must contain:

20+ real scholarship records
15+ verified against primary/official sources
10+ records with confidence ≥95%
3+ different source types
2+ change detection examples
2+ expired/stale examples

All records must be authentic and traceable.

26. Demonstration Flow

The working demonstration should show the complete lifecycle:

Start crawler
      ↓
Discover scholarship
      ↓
Identify official source
      ↓
Crawl source
      ↓
Extract information
      ↓
Normalize into structured format
      ↓
Collect source evidence
      ↓
Verify information
      ↓
Calculate confidence
      ↓
Store scholarship
      ↓
Display in dashboard
      ↓
Run crawler again
      ↓
Discover new scholarship
      ↓
Re-check existing scholarship
      ↓
Detect change
      ↓
Store change history
      ↓
Detect expired/stale scholarship
      ↓
Update dashboard
27. Technical Architecture

The system should conceptually contain:

                 DISCOVERY
                     │
                     ▼
              SOURCE CLASSIFIER
                     │
                     ▼
                  CRAWLER
                     │
                     ▼
                EXTRACTION
                     │
                     ▼
                NORMALIZER
                     │
                     ▼
               VERIFICATION
                     │
                     ▼
             CONFIDENCE ENGINE
                     │
                     ▼
                  DATABASE
      0              │
          ┌──────────┴──────────┐
          ▼                     ▼
   CHANGE DETECTION         STATUS ENGINE
          │                     │
          └──────────┬──────────┘
                     ▼
                 DASHBOARD

A scheduler operates outside the pipeline and periodically triggers new runs.

28. AI vs Deterministic Components

AI should primarily be used for tasks where semantic understanding is useful:

Discovery assistance
Information extraction
Eligibility interpretation
Source/evidence matching

Deterministic code should handle:

Scheduling
Database operations
Hash comparison
Change detection
Date calculations
Status transitions
Confidence calculation
History management

This separation helps maintain reliability.

29. Reliability Principles

The system should follow these principles:

Never invent missing data
Unknown → Not specified
Prefer primary sources
Official source > Aggregator
Preserve evidence
Every important value → source evidence
Preserve history
Old value → Change History → New value
Make confidence explainable
Score → Evidence-based reasons
Re-verify continuously
Database ≠ permanent truth

The official source remains the source of truth.

30. Final Deliverables
A. Working Application

A functional crawler and dashboard.

Preferably:

Live URL

or alternatively:

Local setup instructions
B. GitHub Repository

Include:

Source code
README
Requirements
Database schema
Configuration
Sample data
Setup instructions
C. Demonstration

Show:

Crawler
→ Discovery
→ Crawl
→ Extraction
→ Verification
→ Confidence
→ Storage
→ Dashboard
→ Second Run
→ Change Detection
→ Status Update
D. Technical Note

Maximum 3 pages covering:

Architecture
Technology choices
Discovery methodology
Extraction methodology
Verification methodology
Confidence methodology
Anti-hallucination approach
Change detection
31. Success Criteria

The project is successful if an evaluator can answer YES to all of these:

✓ Can the system discover scholarships?
✓ Can it find new scholarships beyond fixed records?
✓ Can it crawl real websites?
✓ Can it extract structured information?
✓ Can it identify the official source?
✓ Can every important field be supported by evidence?
✓ Can it avoid hallucinating missing information?
✓ Can it calculate a deterministic confidence score?
✓ Can it distinguish VERIFIED from REVIEW_REQUIRED?
✓ Can it store scholarships persistently?
✓ Can it run repeatedly?
✓ Can it detect changes?
✓ Can it preserve old values?
✓ Can it detect expired scholarships?
✓ Can it detect unavailable/stale sources?
✓ Can I search the resulting scholarships?
✓ Can I inspect the evidence?
✓ Can I see the change history?
✓ Are there 20+ real scholarships?
✓ Are 15+ verified using primary sources?
✓ Are 10+ ≥95% confidence?