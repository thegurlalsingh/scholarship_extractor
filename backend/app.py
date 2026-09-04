"""
FastAPI application that acts as the bridge between Supabase and the Python pipeline.
It exposes HTTP endpoints for triggering scholarship crawls and rechecks (called by pg_cron
via pg_net), checking run status, and streaming live backend logs to the dashboard terminal
via Server-Sent Events.
"""

from dotenv import load_dotenv

load_dotenv()

import sys
import collections
import asyncio
from fastapi.responses import StreamingResponse

MAX_LOGS = 1000
log_queue = collections.deque(maxlen=MAX_LOGS)


class LogCaptureStream:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, data):
        self.original_stream.write(data)
        stripped = data.strip()
        if stripped:
            log_queue.append(stripped)

    def flush(self):
        self.original_stream.flush()


sys.stdout = LogCaptureStream(sys.stdout)
sys.stderr = LogCaptureStream(sys.stderr)

from typing import Optional
from fastapi import Depends, FastAPI, BackgroundTasks
from pydantic import BaseModel, Field

from monitoring.cred_check_supabase import verify_recheck_secret
from database.supabase import get_store
from monitoring.recheck import RecheckService
from orchestrator.orchestrator import run_pipeline
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Scholarship Recheck API",
    description="Internal API that Supabase pg_cron hits to trigger scholarship rechecks.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecheckRequest(BaseModel):
    batch_size: int = Field(default=25, ge=1, le=200)
    stale_after_hours: int = Field(default=24, ge=1)
    include_inactive: bool = False


@app.get("/health")
def health():
    """Unauthenticated - for uptime checks only, reveals nothing sensitive."""
    return {"status": "ok"}


@app.get("/recheck/last-run")
def last_recheck_run():
    """
    For a "last updated on" indicator on a dashboard. Reads
    recheck_runs (see recheck_runs_migration.sql), not
    cron.job_run_details - the latter only proves the cron fired, not
    that the recheck actually finished.

    Left unauthenticated like /health since it's read-only aggregate
    counts, no scholarship content or secrets. If your dashboard is
    itself public-facing, put this behind your own dashboard backend
    rather than calling it straight from a browser.
    """

    store = get_store()

    last_run = store.get_last_recheck_run()

    return {"last_run": last_run}


@app.post("/recheck/run", dependencies=[Depends(verify_recheck_secret)])
def run_recheck(payload: RecheckRequest = RecheckRequest()):
    """
    Triggered by pg_cron/pg_net on a timer (see recheck_cron_schedule.sql),
    or manually for testing. Runs synchronously and returns a summary -
    keep `batch_size` modest so a run comfortably finishes inside
    whatever request timeout sits in front of this (pg_net's
    timeout_milliseconds, any reverse proxy, etc.).
    """

    store = get_store()

    service = RecheckService(store)

    summary = service.run(
        batch_size=payload.batch_size,
        stale_after_hours=payload.stale_after_hours,
        only_active=not payload.include_inactive,
    )

    return summary


@app.post("/recheck/manual")
def run_recheck_manual(
    background_tasks: BackgroundTasks,
    payload: RecheckRequest = RecheckRequest(),
):
    """
    Triggered manually from the dashboard. Runs asynchronously in the background.
    """
    store = get_store()
    service = RecheckService(store)

    background_tasks.add_task(
        service.run,
        batch_size=payload.batch_size,
        stale_after_hours=payload.stale_after_hours,
        only_active=not payload.include_inactive,
    )

    return {
        "status": "accepted",
        "message": "Scholarship recheck run started in the background."
    }


@app.get("/recheck/status")
def get_recheck_status():
    """
    Check if a recheck run is currently active.
    """
    store = get_store()
    try:
        if hasattr(store, 'client'):
            result = store.client.table("recheck_runs").select("id,started_at").eq("status", "RUNNING").limit(1).execute()
            if result.data:
                return {"running": True, "run": result.data[0]}
    except Exception as e:
        print(f"Error checking recheck status: {e}")
    return {"running": False}


class OrchestratorRequest(BaseModel):
    max_domains: int = Field(default=5, ge=1, le=50)
    max_depth: int = Field(default=2, ge=1, le=10)
    max_pages: int = Field(default=15, ge=1, le=100)
    start_url: Optional[str] = Field(default=None)
    skip_db: bool = Field(default=False)


@app.post("/orchestrator/run", dependencies=[Depends(verify_recheck_secret)])
def run_orchestrator(
    background_tasks: BackgroundTasks,
    payload: OrchestratorRequest = OrchestratorRequest(),
):
    """
    Trigger the end-to-end scholarship discovery and crawling pipeline.
    Runs asynchronously in the background since crawling can take minutes.
    """
    background_tasks.add_task(
        run_pipeline,
        start_url=payload.start_url,
        max_domains=payload.max_domains,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        skip_db=payload.skip_db,
    )
    return {
        "status": "accepted",
        "message": "Orchestrator pipeline run started in the background.",
    }


@app.post("/orchestrator/manual")
def run_orchestrator_manual(
    background_tasks: BackgroundTasks,
    payload: OrchestratorRequest = OrchestratorRequest(),
):
    """
    Trigger the end-to-end pipeline manually from the dashboard.
    Runs asynchronously in the background.
    """
    background_tasks.add_task(
        run_pipeline,
        start_url=payload.start_url,
        max_domains=payload.max_domains,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        skip_db=payload.skip_db,
    )
    return {
        "status": "accepted",
        "message": "Orchestrator pipeline run started in the background.",
    }


@app.get("/orchestrator/status")
def get_orchestrator_status():
    """
    Check if a crawl/discovery run is currently active.
    """
    store = get_store()
    try:
        if hasattr(store, 'client'):
            # Check crawl_runs
            crawl_res = store.client.table("crawl_runs").select("id,started_at").eq("status", "RUNNING").limit(1).execute()
            # Check discovery_runs
            disc_res = store.client.table("discovery_runs").select("id,started_at").eq("status", "RUNNING").limit(1).execute()

            if crawl_res.data or disc_res.data:
                return {
                    "running": True,
                    "crawl_run": crawl_res.data[0] if crawl_res.data else None,
                    "discovery_run": disc_res.data[0] if disc_res.data else None
                }
    except Exception as e:
        print(f"Error checking orchestrator status: {e}")
    return {"running": False}


@app.get("/logs/stream")
def stream_logs():
    """
    Server-Sent Events (SSE) endpoint to stream backend execution logs to the frontend terminal.
    """
    async def event_generator():
        yield "data: [SYSTEM] Connected to backend live log stream.\n\n"
        last_index = max(0, len(log_queue) - 50) # send last 50 logs as context
        while True:
            if last_index < len(log_queue):
                while last_index < len(log_queue):
                    yield f"data: {log_queue[last_index]}\n\n"
                    last_index += 1
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )