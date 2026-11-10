"""Scheduler entrypoint: GitHub Actions cron calls POST /api/jobs/daily with the shared secret."""

import hmac

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from .. import routine
from ..config import settings
from ..db import SessionLocal

router = APIRouter(prefix="/api/jobs")


def _run() -> None:
    with SessionLocal() as db:
        routine.run(db)


@router.post("/daily", status_code=202)
def daily(bg: BackgroundTasks, x_cron_secret: str = Header("")):
    if not hmac.compare_digest(x_cron_secret, settings().cron_secret):
        raise HTTPException(403, "Bad cron secret")
    bg.add_task(_run)
    return {"started": True}
