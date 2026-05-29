from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.system import SystemStatusRead

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusRead)
def system_status(db: Session = Depends(get_db)) -> SystemStatusRead:
    settings = get_settings()
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database = "error"

    storage = "ok" if Path(settings.storage_path).exists() else "error"
    redis = "ok" if settings.redis_url else "not_configured"
    worker = "ok" if settings.redis_url else "not_configured"
    vector_db = "ok" if settings.qdrant_url else "not_configured"

    llm_model = settings.llm_model.lower()
    llm_base_url = settings.llm_base_url.lower()
    llm = "mock" if "stub" in llm_model or "mock" in llm_model or "8010" in llm_base_url else "configured"

    return SystemStatusRead(
        backend="ok",
        database=database,
        storage=storage,
        redis=redis,
        worker=worker,
        vector_db=vector_db,
        llm=llm,
        fns_provider=settings.fns_provider,
        fns_mode=settings.fns_provider_mode,
        fns_sandbox_enabled=settings.enable_fns_sandbox,
        real_fns_enabled=settings.enable_real_fns,
        russian_post_provider=settings.russian_post_provider,
        russian_post_mode=settings.russian_post_mode,
        russian_post_sandbox_enabled=settings.enable_russian_post_sandbox,
        real_post_send_enabled=settings.enable_real_post_send,
        court_arbitr_provider=settings.court_arbitr_provider,
        court_arbitr_mode=settings.court_provider_mode,
        court_sandbox_enabled=settings.enable_court_sandbox,
        real_court_search_enabled=settings.enable_real_court_search,
        public_kad_search_enabled=settings.enable_public_kad_search,
        court_submission_enabled=settings.enable_court_submission,
    )
