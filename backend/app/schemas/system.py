from pydantic import BaseModel


class SystemStatusRead(BaseModel):
    backend: str
    database: str
    storage: str
    redis: str
    worker: str
    vector_db: str
    llm: str
    fns_provider: str
    fns_mode: str
    fns_sandbox_enabled: bool
    real_fns_enabled: bool
    russian_post_provider: str
    russian_post_mode: str
    russian_post_sandbox_enabled: bool
    real_post_send_enabled: bool
    court_arbitr_provider: str
    court_arbitr_mode: str
    court_sandbox_enabled: bool
    real_court_search_enabled: bool
    public_kad_search_enabled: bool
    court_submission_enabled: bool
