# Secrets Policy

## Sensitive Keys

Treat any setting or payload field containing one of these markers as secret:

- `TOKEN`
- `SECRET`
- `PASSWORD`
- `API_KEY`
- `APP_TOKEN`
- `USER_KEY`
- `AUTH`
- `KEY`

This includes sandbox credentials such as:

- `FNS_SANDBOX_TOKEN`
- `FNS_SANDBOX_CLIENT_ID`
- `FNS_SANDBOX_CLIENT_SECRET`
- `RUSSIAN_POST_SANDBOX_APP_TOKEN`
- `RUSSIAN_POST_SANDBOX_USER_KEY`
- `RUSSIAN_POST_SANDBOX_CLIENT_SECRET`
- `COURT_SANDBOX_TOKEN`
- `COURT_PROVIDER_SANDBOX_API_KEY`
- `COURT_SANDBOX_CLIENT_SECRET`

## Rules

- Secrets are read only from env or secret storage.
- Frontend never receives raw secret values.
- `AuditLog` never stores raw secrets.
- `IntegrationRequestLog` never stores raw secrets.
- Test-connection responses never return secrets.
- Export packages never include secrets.

## Masking

- Sensitive values exposed through settings APIs are returned as `[REDACTED]`.
- Audit and integration logs may keep only safe metadata and the fact of change.

## Prohibited

- Committing credentials to the repository.
- Logging raw tokens in application logs.
- Returning raw credentials in API responses.
- Embedding credentials in mock data, tests, or frontend fixtures.
