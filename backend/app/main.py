import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.models import Role, RoleName, SystemSetting, User


settings = get_settings()


def initialize_app() -> None:
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        seed_defaults()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_app()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "request_id": request.state.request_id})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request.state.request_id})


def seed_defaults() -> None:
    with Session(engine) as db:
        for role_name in RoleName:
            if not db.scalar(select(Role).where(Role.name == role_name.value)):
                db.add(Role(name=role_name.value))
        db.commit()

        seeds = [
            (settings.admin_email, "System Admin", RoleName.admin.value),
            (settings.lawyer_email, "Lead Lawyer", RoleName.lawyer.value),
            (settings.manager_email, "Operations Manager", RoleName.manager.value),
            (settings.initiator_email, "Case Initiator", RoleName.initiator.value),
            (settings.service_agent_email, "Service Agent", RoleName.service_agent.value),
        ]
        for email, full_name, role_name in seeds:
            if db.scalar(select(User).where(User.email == email)):
                continue
            role = db.scalar(select(Role).where(Role.name == role_name))
            db.add(User(email=email, full_name=full_name, password_hash=hash_password(settings.seed_password), role_id=role.id))
        if not db.scalar(select(SystemSetting).where(SystemSetting.key == "llm.mode")):
            db.add(SystemSetting(key="llm.mode", value="stub", description="Local LLM mode"))
        db.commit()

app.include_router(api_router, prefix=settings.api_prefix)
