from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Role, RoleName, User


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def pytest_addoption(parser):
    parser.addoption(
        "--run-sandbox",
        action="store_true",
        default=False,
        help="Run live sandbox credential checks when credentials are present.",
    )


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        for role_name in RoleName:
            db.add(Role(name=role_name.value))
        db.commit()
        role_map = {role.name: role.id for role in db.scalars(select(Role))}
        seeds = [
            ("admin@example.com", "System Admin", RoleName.admin.value),
            ("lawyer@example.com", "Lead Lawyer", RoleName.lawyer.value),
            ("manager@example.com", "Operations Manager", RoleName.manager.value),
            ("initiator@example.com", "Case Initiator", RoleName.initiator.value),
            ("service-agent@example.com", "Service Agent", RoleName.service_agent.value),
        ]
        for email, full_name, role_name in seeds:
            db.add(
                User(
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password("ChangeMe123!"),
                    role_id=role_map[role_name],
                )
            )
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seed_users() -> dict[str, dict[str, str]]:
    return {
        "admin": {"email": "admin@example.com", "password": "ChangeMe123!"},
        "lawyer": {"email": "lawyer@example.com", "password": "ChangeMe123!"},
        "manager": {"email": "manager@example.com", "password": "ChangeMe123!"},
        "initiator": {"email": "initiator@example.com", "password": "ChangeMe123!"},
        "service_agent": {"email": "service-agent@example.com", "password": "ChangeMe123!"},
    }


@pytest.fixture
def auth_headers(client: TestClient, seed_users: dict[str, dict[str, str]]) -> Callable[[str], dict[str, str]]:
    def factory(role: str) -> dict[str, str]:
        credentials = seed_users[role]
        response = client.post("/api/auth/login", json=credentials)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture
def sample_documents_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "documents"


@pytest.fixture
def run_sandbox_live(request) -> bool:
    return bool(request.config.getoption("--run-sandbox"))
