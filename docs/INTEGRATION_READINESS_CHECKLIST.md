# Integration Readiness Checklist

- Legal basis for API access is documented.
- Technical API documentation has been reviewed.
- Sandbox credentials are separate from production credentials.
- Production credentials are not used in dev, test, demo, or pilot.
- Real API flags are `false` by default.
- Sandbox flags are `false` by default.
- Secrets are stored only in env or secret storage.
- Frontend does not receive tokens, passwords, or raw credentials.
- `AuditLog` does not contain secrets.
- `IntegrationRequestLog` does not contain secrets or raw credentials.
- Timeout, retry, backoff, and rate-limit policy is defined per adapter.
- Idempotency exists for postal create/send and court import.
- Dry-run exists for dangerous operations.
- Test-connection endpoints are safe in mock, manual, disabled, and sandbox-ready modes.
- Sandbox enablement requires approval with expiry.
- Rollback path exists back to mock/manual mode.
- Real API enablement requires separate approval and separate sprint.
