# Scholarship Intelligence Crawler & Dashboard

An end-to-end automated pipeline that continuously discovers, crawls, extracts, verifies, scores, and monitors real scholarship opportunities for Indian students. The system is designed to produce trustworthy, hallucination-free scholarship data backed by traceable official sources — not aggregator websites or AI-invented information.

---

## What This System Does

The pipeline runs in seven stages, fully automated:

```
Search Engine Queries
       ↓
Candidate Discovery & Source Classification
       ↓
Recursive Portal Crawling (legacy SSL support)
       ↓
Deterministic Extraction + LLM Fallback
       ↓
Anti-Hallucination Title Filter
       ↓
7-Signal Legitimacy Scoring (0–100 pts)
       ↓
Supabase PostgreSQL Storage
       ↓
Daily Recheck Worker (drift detection, liveness, expiry)
       ↓
React Dashboard + Live SSE Terminal
```

On every re-run, the system compares newly crawled data against what is already stored. Changed fields are logged with old value, new value, and detection timestamp. Scholarships that are no longer reachable are flagged and eventually deactivated.

---

## Key Features

- **280+ search dork queries** covering Government (Central + State), UGC/AICTE/Ministries, Universities, Corporate CSR, Foundations, and special eligibility categories (SC/ST, minorities, girls, differently-abled).
- **Recursive crawler** that follows internal links up to a configurable depth, with built-in retries for old government servers that use outdated SSL certificates.
- **Deterministic extraction** for dates, amounts, eligibility rules, domicile requirements, and application URLs — falls back to an open-source LLM (via OpenRouter free tier) only when deterministic parsing finds nothing.
- **Anti-hallucination guard**: the extracted scheme name must literally appear in the raw page text, or the record is dropped. No field is ever guessed — missing values are stored as `null`, never fabricated.
- **7-signal confidence score** (0–100 points) based on real evidence checks: domain trust, URL reachability, PDF guide presence, date validity, and more.
- **Field-level change detection**: each recheck compares 13 tracked fields against stored values and logs every difference separately with an audit timestamp.
- **Computed status**: `ACTIVE`, `EXPIRING_SOON` (≤7 days), `EXPIRED` (deadline passed), `NO_LONGER_VERIFIABLE` (URL fails 3 consecutive checks).
- **Live SSE terminal** on the dashboard streams every backend `print()` log in real time.

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Pipeline Core | Python 3.12 | Strong ecosystem for scraping, parsing, and HTTP |
| API Mediator | FastAPI + Uvicorn | Async-native, handles SSE and background tasks cleanly |
| Database | Supabase PostgreSQL | Managed DB with pg_cron, trigger functions, and REST API |
| Search | DuckDuckGo (`ddgs`) | No API key required, no rate-limit costs |
| HTML Parsing | BeautifulSoup4 | Robust, tolerates malformed government portal HTML |
| LLM Fallback | OpenRouter free tier | Used only on listing pages when deterministic parsing fails |
| Frontend | React 19 + Vite + Tailwind CSS v3 | Fast compilation, reactive state, utility-first styling |

---

## Database Design

Six tables, partitioned by pipeline stage, connected by foreign keys.

```
discovery_runs ──► discovery_candidates
                        │
                        ▼
                   crawl_runs ──► crawl_pages ──► scholarships
                                                       │
                                   ┌───────────────────┤
                                   ▼                   ▼
                         scholarship_monitoring   scholarship_validations
                                   │
                                   ▼
                         scholarship_changes (audit log)
```

### `scholarships` — core record
Stores the structured scholarship data extracted from official source pages.

Key fields: `title`, `organization`, `scheme_type` (MERIT_BASED / WELFARE_BASED), `application_start`, `application_end`, `source_url`, `guidelines_url`, `faq_url`, `application_url`, `scholarship_amount`, `education_level`, `income_criteria`, `gender_criteria`, `category_criteria`, `domicile`, `is_active`, `computed_status`.

### `scholarship_validations` — confidence scoring log
One row per validation run. Stores the detailed verification checklist as JSONB, individual warnings, and a source domain snapshot used for traceability.

Key fields: `status` (VERIFIED / HIGH_CONFIDENCE / LIKELY_VALID / NEEDS_REVIEW / LOW_CONFIDENCE), `legitimacy_score` (0–100), `confidence` (0.00–1.00), `verification_checks` (JSONB), `warnings` (JSONB), `source_snapshot` (JSONB).

### `scholarship_monitoring` — recheck state
One row per scholarship (auto-created by a DB trigger on insert). Tracks when it was last checked and how many times in a row it has failed reachability.

Key fields: `last_checked_at`, `is_active`, `consecutive_failures`.

### `scholarship_changes` — audit trail
One row per detected change. Never overwrites; always appends.

Key fields: `field_name`, `old_value`, `new_value`, `change_type` (FIELD_UPDATED / MARKED_INACTIVE / REACTIVATED), `detected_at`.

### DB Triggers
- `trg_create_monitoring_row` — auto-creates a monitoring row when a scholarship is inserted so the recheck worker never has a missing entry.
- `trg_sync_active_status` — when the recheck worker changes `is_active` in `scholarship_monitoring`, this trigger syncs it back to `scholarships.is_active` automatically.

---

## Verification & Confidence Score Methodology

The confidence score is not generated by an AI model. It is calculated by running explicit evidence checks, each worth a fixed number of points:

```
Check 1 — Title present on page              →  10 pts
Check 2 — Government domain (.gov.in, etc.)  →  30 pts
          Known trusted domain               →  15 pts
Check 3 — Source URL returns HTTP 200        →  20 pts
Check 4 — Guidelines PDF reachable           →  15 pts
Check 5 — FAQ URL reachable                  →  10 pts
Check 6 — Title contains scholarship keyword →  10 pts
Check 7 — Application dates are a valid range →  5 pts
                                      Total:   100 pts
```

Status mapping:
- **VERIFIED** — Score ≥ 80 and source is a government official domain.
- **HIGH_CONFIDENCE** — Score ≥ 80 but source is a non-government trusted domain.
- **LIKELY_VALID** — Score 60–79.
- **NEEDS_REVIEW** — Score 40–59.
- **LOW_CONFIDENCE** — Score < 40.

---

## Anti-Hallucination Approach

Three layers prevent fabricated data from entering the database:

1. **Title containment check** — the extracted scheme name must appear as a literal substring in the raw page HTML. If not, the record is dropped before any DB write.
2. **Null-first policy** — the extractor explicitly returns `None` for every field it cannot find evidence for. It never fills in a "reasonable guess." The DB stores `null`, not an invented value.
3. **LLM prompt constraints** — when the LLM fallback is invoked, the prompt explicitly instructs the model to output `null` for missing fields and prohibits inferring values. The model is given the actual page text, not asked to recall from training.

---

## Change Detection

The recheck worker runs daily (or on manual trigger). For each scholarship:

1. Re-fetches the source URL using the same crawler (with SSL retry logic).
2. If fetch fails or the scholarship title disappears from the page, increments `consecutive_failures`.
3. At 3 consecutive failures, flips `is_active = false` and sets `computed_status = NO_LONGER_VERIFIABLE`. Logs a `MARKED_INACTIVE` event.
4. If fetch succeeds, resets failures to 0. Re-extracts 13 tracked fields and diffs them against stored values.
5. Any field that changed gets a `FIELD_UPDATED` row in `scholarship_changes` with the old value, new value, and detection timestamp.
6. If a previously inactive scholarship is reachable again, it is reactivated and a `REACTIVATED` event is logged.

---

## Repository Structure

```
scholarship_automation/
├── backend/
│   ├── app.py                          FastAPI app — API routes, SSE log stream, background task triggers
│   ├── requirements.txt
│   ├── .env                            Environment variables (not committed)
│   ├── config/                         Shared configuration constants
│   ├── crawler/
│   │   ├── candidate_classifier.py     Decides if a URL is a scholarship listing or detail page
│   │   ├── page_classifier.py          Classifies crawled pages (LISTING / DETAIL / IRRELEVANT)
│   │   ├── page_crawler.py             Fetches a single URL with retry and SSL fallback
│   │   ├── portal_crawler.py           Recursively crawls a portal up to max_depth / max_pages
│   │   ├── scholarship_extractor.py    Extracts structured fields deterministically, LLM fallback
│   │   └── link_extractor.py           Pulls candidate links from a crawled page
│   ├── database/
│   │   ├── supabase.py                 Supabase client wrapper — all read/write operations
│   │   ├── discovery_node.sql          Schema for discovery_runs and discovery_candidates
│   │   ├── crawler_node.sql            Schema for crawl_runs and crawl_pages
│   │   ├── scholarships_node.sql       Schema for scholarships and scholarship_validations
│   │   ├── recheck_migration.sql       Schema for monitoring, changes, triggers, and recheck_runs
│   │   └── schema_extension.sql        Adds extended fields (amount, eligibility, computed_status)
│   ├── discovery/
│   │   ├── candidate.py                ScholarshipCandidate dataclass
│   │   ├── candidate_classifier.py     Classifies candidates as scholarship-relevant or not
│   │   ├── discovery_engine.py         Runs all search strategies and deduplicates candidates
│   │   ├── search_provider.py          DuckDuckGo search wrapper
│   │   ├── source_classifier.py        Maps domain to source type (GOVERNMENT / UNIVERSITY / etc.)
│   │   └── strategies.py              280+ categorized search dork queries
│   ├── monitoring/
│   │   ├── recheck.py                  RecheckService — field diffing, liveness, status updates
│   │   └── cred_check_supabase.py      API secret verification for protected endpoints
│   ├── orchestrator/
│   │   └── orchestrator.py             Wires together discovery → crawl → extract → validate → store
│   └── validator/
│       └── scholarship_validator.py    7-signal evidence-based confidence scorer
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     React Router setup and global data refresh
│   │   ├── supabaseClient.js           Supabase JS client (service role key)
│   │   └── components/
│   │       ├── Dashboard.jsx           Summary stats and health cards
│   │       ├── ScholarshipTable.jsx    Searchable, filterable scholarship list
│   │       ├── ScholarshipDetails.jsx  Detail view with Verification, Changes, and Evidence tabs
│   │       ├── Monitoring.jsx          Pipeline health monitoring page
│   │       ├── Terminal.jsx            Live SSE log terminal
│   │       ├── Sidebar.jsx             Navigation sidebar
│   │       └── Skeleton.jsx            Loading skeleton components
└── README.md                           This file
```

---

## Setup & Installation

### 1. Environment Variables

Create `backend/.env`:
```env
OPENROUTER_API_KEY=your_openrouter_free_api_key
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
RECHECK_API_SECRET=any_long_random_string
```

### 2. Database Migrations

Run these SQL files in your Supabase SQL Editor **in this exact order**:

```
1. backend/database/discovery_node.sql
2. backend/database/crawler_node.sql
3. backend/database/scholarships_node.sql
4. backend/database/recheck_migration.sql
5. backend/database/schema_extension.sql
```

### 3. Start the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app:app --port 8000
```

Check it's alive: `curl http://localhost:8000/health` → `{"status": "ok"}`

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Running the Pipeline

**Trigger a full discovery + crawl cycle:**
```bash
curl -X POST http://localhost:8000/orchestrator/manual \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 15}'
```

**Trigger a recheck cycle (change detection + status updates):**
```bash
curl -X POST http://localhost:8000/recheck/manual \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 10}'
```

**Watch live logs:** Open the **Terminal** tab in the dashboard at `http://localhost:5173`.

**Inspect verification evidence:** Click any scholarship row → **Verification Details** tab → see the exact point breakdown, source domain snapshot, and any warnings.
