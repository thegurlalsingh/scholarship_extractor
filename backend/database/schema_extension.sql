-- ============================================================
-- MIGRATION: Extended scholarship schema
--
-- Adds the fields required by the assignment's minimum schema:
--   scholarship_amount, education_level, application_url,
--   income_criteria, gender_criteria, category_criteria,
--   domicile, eligibility_summary, documents_required,
--   selection_process, computed_status
--
-- All new columns are nullable TEXT so existing rows are safe.
-- computed_status is kept in sync at read-time by the frontend
-- (ACTIVE / EXPIRING_SOON / EXPIRED / REVIEW_REQUIRED /
--  NO_LONGER_VERIFIABLE) — it is also written by the recheck
-- service when a scholarship is marked inactive.
-- ============================================================

ALTER TABLE scholarships
    ADD COLUMN IF NOT EXISTS scholarship_amount    TEXT,
    ADD COLUMN IF NOT EXISTS education_level       TEXT,
    ADD COLUMN IF NOT EXISTS application_url       TEXT,
    ADD COLUMN IF NOT EXISTS income_criteria       TEXT,
    ADD COLUMN IF NOT EXISTS gender_criteria       TEXT,
    ADD COLUMN IF NOT EXISTS category_criteria     TEXT,
    ADD COLUMN IF NOT EXISTS domicile              TEXT,
    ADD COLUMN IF NOT EXISTS eligibility_summary   TEXT,
    ADD COLUMN IF NOT EXISTS documents_required    TEXT,
    ADD COLUMN IF NOT EXISTS selection_process     TEXT,
    ADD COLUMN IF NOT EXISTS computed_status       TEXT
        CHECK (
            computed_status IS NULL
            OR computed_status IN (
                'ACTIVE',
                'EXPIRING_SOON',
                'EXPIRED',
                'REVIEW_REQUIRED',
                'NO_LONGER_VERIFIABLE'
            )
        );

-- Index for computed_status queries (filtering by active/expired)
CREATE INDEX IF NOT EXISTS idx_scholarships_computed_status
    ON scholarships(computed_status);

-- ============================================================
-- Backfill computed_status for all existing rows:
--   - expired (application_end in the past)  → EXPIRED
--   - expiring soon (≤7 days left)           → EXPIRING_SOON
--   - inactive (no longer reachable)         → NO_LONGER_VERIFIABLE
--   - everything else active                 → ACTIVE
-- ============================================================

UPDATE scholarships
SET computed_status =
    CASE
        WHEN is_active = FALSE
            THEN 'NO_LONGER_VERIFIABLE'
        WHEN application_end IS NOT NULL
             AND application_end < CURRENT_DATE
            THEN 'EXPIRED'
        WHEN application_end IS NOT NULL
             AND application_end BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
            THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END
WHERE computed_status IS NULL;
