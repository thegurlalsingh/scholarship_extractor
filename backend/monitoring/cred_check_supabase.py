# api/auth.py
#
# Shared-secret check for endpoints that Supabase calls from the
# outside (via pg_cron + pg_net). This is NOT Supabase Auth / RLS -
# pg_net just makes a plain HTTPS request from Postgres, so this
# header check is the only thing standing between the endpoint and
# the open internet.
#
# Set RECHECK_API_SECRET to a long random value in this service's
# env, and put the SAME value in Supabase Vault (see
# recheck_cron_schedule.sql) - never in source, never in a query
# string/URL.

import hmac
import os

from fastapi import Header, HTTPException, status


def verify_recheck_secret(x_recheck_secret: str = Header(default=None)) -> None:

    expected = os.environ.get("RECHECK_API_SECRET")

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RECHECK_API_SECRET is not configured on this server.",
        )

    if not x_recheck_secret or not hmac.compare_digest(x_recheck_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Recheck-Secret header.",
        )