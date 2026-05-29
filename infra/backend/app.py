import os

from fastapi import FastAPI


app = FastAPI(title="Legal AI Backend Stub", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend-stub", "app_env": os.getenv("APP_ENV", "local")}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "backend-stub", "message": "Stub backend is running"}
