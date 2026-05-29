import os

import pytest


def _credentials_present(prefixes: tuple[str, ...]) -> bool:
    return all(bool(os.getenv(name, "").strip()) for name in prefixes)


def _require_live(requested: bool, present: bool, reason: str):
    if not requested:
        pytest.skip("run with --run-sandbox to execute live sandbox credential checks")
    if not present:
        pytest.skip(reason)


def test_live_fns_sandbox_connection_skip_safe(client, auth_headers, run_sandbox_live):
    _require_live(
        run_sandbox_live,
        _credentials_present(("FNS_SANDBOX_TOKEN", "FNS_SANDBOX_CLIENT_ID", "FNS_SANDBOX_CLIENT_SECRET")),
        "FNS sandbox credentials are not configured in the environment",
    )
    admin_headers = auth_headers("admin")
    response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
    assert response.status_code == 200


def test_live_russian_post_sandbox_connection_skip_safe(client, auth_headers, run_sandbox_live):
    _require_live(
        run_sandbox_live,
        _credentials_present(
            (
                "RUSSIAN_POST_SANDBOX_APP_TOKEN",
                "RUSSIAN_POST_SANDBOX_USER_KEY",
                "RUSSIAN_POST_SANDBOX_CLIENT_SECRET",
            )
        ),
        "Russian Post sandbox credentials are not configured in the environment",
    )
    admin_headers = auth_headers("admin")
    response = client.post("/api/russian-post/test-connection?sandbox=true", headers=admin_headers)
    assert response.status_code == 200


def test_live_court_sandbox_connection_skip_safe(client, auth_headers, run_sandbox_live):
    _require_live(
        run_sandbox_live,
        any(
            bool(os.getenv(name, "").strip())
            for name in ("COURT_SANDBOX_TOKEN", "COURT_PROVIDER_SANDBOX_API_KEY", "COURT_SANDBOX_CLIENT_SECRET")
        ),
        "Court sandbox credentials are not configured in the environment",
    )
    admin_headers = auth_headers("admin")
    response = client.post("/api/court-arbitr/test-connection?sandbox=true", headers=admin_headers)
    assert response.status_code == 200
