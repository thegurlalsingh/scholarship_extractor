-- ============================================================
-- SUPABASE CRON -> RECHECK API
--
-- This is the Postgres side of the mediator described in api/main.py.
-- Supabase can't run our Python recheck service itself, so instead:
--
--   pg_cron schedules a job on a timer
--     -> pg_net fires an async outbound HTTPS POST
--       -> our deployed FastAPI service (api/main.py), which runs
--          monitoring/recheck_scholarships.py and writes the results
--          straight back into THIS SAME database via database/supabase.py.
--
-- Run this (SQL editor, or as a migration) AFTER:
--   1. recheck_migration.sql has already been applied
--      (scholarship_monitoring / scholarship_changes must exist).
--   2. api/main.py is deployed somewhere public over HTTPS, with
--      SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / RECHECK_API_SECRET
--      set as env vars there.
-- ============================================================

create extension if not exists pg_cron with schema extensions;
create extension if not exists pg_net with schema extensions;


-- ------------------------------------------------------------
-- Store the deployed API's URL + shared secret in Supabase Vault
-- instead of pasting them into the cron job body in plaintext.
-- Run these two ONCE. To rotate the secret later, delete the old
-- vault entry (Vault UI, or `select vault.delete_secret(<uuid>)`)
-- and re-create it - `vault.create_secret` needs a unique name.
-- ------------------------------------------------------------

select vault.create_secret(
    'https://YOUR-DEPLOYED-API-HOST/recheck/run',
    'recheck_api_url'
);

select vault.create_secret(
    'REPLACE_WITH_THE_SAME_LONG_RANDOM_VALUE_AS_THE_RECHECK_API_SECRET_ENV_VAR',
    'recheck_api_secret'
);


-- ------------------------------------------------------------
-- Main schedule: every 30 minutes, ask the API to recheck a batch
-- of ACTIVE scholarships that haven't been checked in the last 24h.
-- Keep batch_size modest - each item in the batch is one outbound
-- HTTP fetch (with retries) on the API's side, so a huge batch risks
-- not finishing before pg_net's own request timeout.
-- ------------------------------------------------------------

select cron.schedule(
    'scholarship-recheck-every-30-min',
    '*/30 * * * *',
    $$
    select net.http_post(
        url := (
            select decrypted_secret
            from vault.decrypted_secrets
            where name = 'recheck_api_url'
        ),
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'X-Recheck-Secret', (
                select decrypted_secret
                from vault.decrypted_secrets
                where name = 'recheck_api_secret'
            )
        ),
        body := jsonb_build_object(
            'batch_size', 25,
            'stale_after_hours', 6,
            'include_inactive', false
        ),
        timeout_milliseconds := 30000
    ) as request_id;
    $$
);


-- ------------------------------------------------------------
-- Optional second job: much less frequently, also try INACTIVE
-- scholarships, to catch ones that come back online (logged as
-- REACTIVATED in scholarship_changes). Runs once a day since most
-- inactive scholarships stay inactive - no point burning a fetch on
-- every single one every 30 minutes forever.
-- ------------------------------------------------------------

select cron.schedule(
    'scholarship-recheck-inactive-daily',
    '17 3 * * *',
    $$
    select net.http_post(
        url := (
            select decrypted_secret
            from vault.decrypted_secrets
            where name = 'recheck_api_url'
        ),
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'X-Recheck-Secret', (
                select decrypted_secret
                from vault.decrypted_secrets
                where name = 'recheck_api_secret'
            )
        ),
        body := jsonb_build_object(
            'batch_size', 15,
            'stale_after_hours', 6,
            'include_inactive', true
        ),
        timeout_milliseconds := 30000
    ) as request_id;
    $$
);


-- ============================================================
-- HOUSEKEEPING / DEBUGGING (run manually as needed)
-- ============================================================

-- List scheduled jobs:
--   select * from cron.job;

-- Inspect recent HTTP call outcomes (pg_net logs status/response here):
--   select * from net._http_response order by created desc limit 20;

-- Unschedule a job:
--   select cron.unschedule('scholarship-recheck-every-30-min');
--   select cron.unschedule('scholarship-recheck-inactive-daily');
