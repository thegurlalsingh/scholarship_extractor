# Scholarship Intelligence Crawler

### Technical Architecture & Implementation Note

## 1. System Overview

An automated pipeline that **discovers → crawls → extracts → verifies → scores → stores → continuously rechecks** authentic scholarship opportunities for Indian students.

```text
             ┌─────────────────────┐
             │  Search Discovery   │
             │  280+ targeted      │
             │  queries             │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ Candidate Classifier│
             │ Gov / University /  │
             │ CSR / NGO / Other   │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ Recursive Crawler   │
             │ HTML + PDF + SSL    │
             │ retry handling      │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ Extraction Engine   │
             │ Deterministic → LLM │
             │ fallback            │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ Verification +      │
             │ Confidence Scoring  │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ Supabase PostgreSQL │
             └──────────┬──────────┘
                        ↓
       ┌────────────────┴────────────────┐
       ↓                                 ↓
┌───────────────┐                 ┌───────────────┐
│ React         │                 │ Daily Recheck │
│ Dashboard     │                 │ via pg_cron   │
└───────────────┘                 └───────┬───────┘
                                         ↓
                                Change / stale detection
```

---

## 2. Requirements

| Requirement                  | Implementation                                                      |
| ---------------------------- | ------------------------------------------------------------------- |
| 20+ real scholarships        | Automated discovery + crawling                                      |
| 15+ verified                 | Official-source validation                                          |
| 10+ confidence ≥95%          | Evidence-based scoring                                              |
| 3+ source types              | Government, University, CSR, NGO etc.                               |
| Change detection             | Field-level audit history                                           |
| Stale/expired detection      | Daily recheck + status computation                                  |
| Official source traceability | Source URL + evidence snapshot                                      |
| Continuous automation        | Supabase `pg_cron` → FastAPI mediator                               |
| Working UI                   | React dashboard                                                     |
| Free tools                   | Python, Supabase, React, DuckDuckGo, open-source/ free-tier tooling |

---

## 3. Technology Choices

| Layer        | Technology                    | Purpose                      |
| ------------ | ----------------------------- | ---------------------------- |
| Backend      | Python 3.12                   | Crawling + extraction        |
| Crawler      | Requests + BeautifulSoup      | HTML crawling/parsing        |
| Search       | DuckDuckGo `ddgs`             | Scholarship discovery        |
| LLM fallback | OpenRouter free-tier model    | Extraction fallback only     |
| API          | FastAPI                       | Pipeline + recheck endpoints |
| Database     | Supabase PostgreSQL           | Persistent storage           |
| Scheduler    | Supabase `pg_cron` + `pg_net` | Automated rechecks           |
| Frontend     | React + Vite                  | Dashboard                    |
| Styling      | Tailwind CSS                  | UI                           |
| Live logs    | SSE                           | Real-time crawler output     |

---

## 4. Discovery Methodology

Discovery is **not limited to manually entered URLs**.

```text
280+ Search Queries
       ↓
Government / University / CSR / NGO /
State / Category / Merit / Need-based
       ↓
Search Results
       ↓
Deduplicate URLs
       ↓
Classify Source
       ↓
Crawl Relevant Candidates
```

Queries target official domains such as:

```text
site:gov.in scholarship
site:ac.in scholarship
site:edu.in scholarship
site:org.in scholarship
```

Source classification uses domain and page signals to identify:

**GOVERNMENT | UNIVERSITY | CORPORATE | NGO/TRUST | INTERNATIONAL | OTHER**

---

## 5. Extraction Methodology

The extractor follows a **deterministic-first** strategy.

```text
Official Page
     ↓
HTML / PDF text
     ↓
Deterministic extraction
     │
     ├── Found → Structured Record
     │
     └── Missing → LLM fallback
                         ↓
                  Structured Record
```

Extracted fields include:

| Category    | Examples                           |
| ----------- | ---------------------------------- |
| Identity    | Name, provider, source             |
| Financial   | Amount / benefit                   |
| Eligibility | Income, gender, category, domicile |
| Education   | Course / education level           |
| Timeline    | Opening / closing date             |
| Application | Application URL                    |
| Documents   | Required documents                 |
| Process     | Selection / renewal                |
| Status      | Active / expired / review          |

**Missing information is stored as `NULL`, never guessed.**

---

## 6. Verification & Confidence

Confidence is **calculated by deterministic evidence checks**, not generated by an LLM.

| Evidence check            |  Points |
| ------------------------- | ------: |
| Scholarship title present |      10 |
| Official/trusted domain   |      30 |
| Source reachable          |      20 |
| Guidelines available      |      15 |
| FAQ/supporting page       |      10 |
| Scholarship terminology   |      10 |
| Valid date range          |       5 |
| **Total**                 | **100** |

```text
Score ≥ 95
     ↓
VERIFIED

Score < 95
     ↓
REVIEW REQUIRED
```

The dashboard also exposes the individual checks so the evaluator can see **why** a scholarship received its score.

---

## 7. Anti-Hallucination

Three safeguards are used:

```text
Source Page
    ↓
Title must exist on source
    ↓
Extracted values require evidence
    ↓
Missing values → NULL
    ↓
LLM only sees actual source text
```

**Important:** the LLM is never asked to invent or estimate scholarship information.

Each record retains:

**Database → Official URL → Source snapshot/evidence → Extracted value**

---

## 8. Database / Schema

```text
discovery_runs
      │
      ↓
discovery_candidates
      │
      ↓
crawl_runs ──→ crawl_pages
                    │
                    ↓
              scholarships
               /    |    \
              ↓     ↓     ↓
     validations monitoring changes
                       ↑
                 recheck_runs
```

### Core tables

| Table                       | Purpose                             |
| --------------------------- | ----------------------------------- |
| `scholarships`              | Current normalized scholarship data |
| `scholarship_validations`   | Confidence + verification evidence  |
| `scholarship_monitoring`    | Recheck state + failures            |
| `scholarship_changes`       | Immutable field-level history       |
| `recheck_runs`              | Recheck execution statistics        |
| `discovery_runs/candidates` | Discovery history                   |
| `crawl_runs/pages`          | Crawl history                       |

### `scholarships` contains

`title`, `organization`, `amount`, `eligibility`, `education_level`, `income_criteria`, `category`, `domicile`, `application_start`, `application_end`, `source_url`, `application_url`, `is_active`, `computed_status`, `updated_at`.

---

## 9. Continuous Change Detection

```text
Supabase pg_cron
       ↓
pg_net POST /recheck
       ↓
FastAPI Mediator
       ↓
Recheck Worker
       ↓
Fetch Official Source
       ↓
Compare with DB
       ↓
 ┌─────┴─────────────┐
 │                   │
No change          Change
 │                   │
 ↓                   ↓
Keep record     Update current value
                + save old value
                + create audit entry
```

Example:

| Field    | Previous    | New         |
| -------- | ----------- | ----------- |
| Deadline | 31 Aug 2026 | 15 Sep 2026 |

`scholarship_changes` retains both values and the detection timestamp.

After **3 consecutive verification failures**, the scholarship is marked:

`NO_LONGER_VERIFIABLE`

Other computed states:

`ACTIVE | EXPIRING_SOON | EXPIRED | NO_LONGER_VERIFIABLE`

---

## 10. Configuration & Setup

### Environment

```env
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENROUTER_API_KEY=...
RECHECK_API_TOKEN=...
```

### Database

Run migrations in Supabase SQL Editor:

```text
1. discovery_node.sql
2. crawler_node.sql
3. scholarships_node.sql
4. recheck_migration.sql
5. schema_extension.sql
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Automation

```text
Supabase pg_cron
      ↓
pg_net
      ↓
POST /recheck
      ↓
FastAPI Mediator
      ↓
Recheck Worker
      ↓
Supabase
```

---

## 11. Sample Output

| Scholarship   | Source                | Status          | Confidence |
| ------------- | --------------------- | --------------- | ---------: |
| Scholarship A | Official Govt. Portal | VERIFIED        |        98% |
| Scholarship B | University Website    | VERIFIED        |        96% |
| Scholarship C | Foundation Website    | REVIEW REQUIRED |        82% |

The React dashboard provides:

**Total Discovered · Verified · Review Required · Active · Expired · Recently Updated · Average Confidence**

and for each scholarship:

**Details · Official Source · Application URL · Verification Evidence · Confidence Breakdown · Change History · Last Verified**

---

## 12. Repository

```text
backend/
├── discovery/
├── crawler/
├── validator/
├── monitoring/
├── orchestrator/
├── database/
└── app.py

frontend/
└── src/
    ├── Dashboard.jsx
    ├── ScholarshipTable.jsx
    ├── ScholarshipDetails.jsx
    ├── Monitoring.jsx
    └── Terminal.jsx
```

The result is a working continuous intelligence pipeline rather than a static scraper: it **discovers new opportunities, verifies them against primary sources, stores evidence, monitors existing records, detects changes, and exposes the results through a dashboard.**
