# Integration Modes

## FNS

- `MOCK_FOR_DEV`: local mock provider, no external calls.
- `MANUAL_UPLOAD`: organization data is entered or uploaded manually.
- `LOCAL_EGRUL_FILES`: local EGRUL files only, no network.
- `FNS_SANDBOX_DISABLED`: sandbox contract exists, sandbox use is blocked.
- `FNS_SANDBOX_READY`: sandbox provider stub is available, but still needs flag, credentials, and approval.
- `FNS_PRODUCTION_DISABLED`: production integration is explicitly disabled.
- `OFFICIAL_FNS_INTEGRATION_DISABLED`: legacy disabled mode for official provider wiring.

Flags:

- `ENABLE_FNS_SANDBOX=false`
- `ENABLE_REAL_FNS=false`

## Russian Post

- `MOCK_FOR_DEV`: local postal mock, no real letters.
- `MANUAL_UPLOAD`: proofs and statuses are uploaded manually.
- `RUSSIAN_POST_SANDBOX_DISABLED`: sandbox contract exists, sandbox use is blocked.
- `RUSSIAN_POST_SANDBOX_READY`: sandbox provider stub is available, but still needs flag, credentials, and approval.
- `RUSSIAN_POST_PRODUCTION_DISABLED`: production send is explicitly disabled.
- `RUSSIAN_POST_OTPRAVKA_API_DISABLED`: official provider mode disabled.
- `RUSSIAN_POST_EZP_API_DISABLED`: EZP provider mode disabled.

Flags:

- `ENABLE_RUSSIAN_POST_SANDBOX=false`
- `ENABLE_REAL_POST_SEND=false`

## Court Arbitr

- `MOCK_FOR_DEV`: mock import and mock case cards.
- `MANUAL_IMPORT`: manual import only.
- `COURT_SANDBOX_DISABLED`: sandbox contract exists, sandbox use is blocked.
- `COURT_SANDBOX_READY`: sandbox provider stub is available, but still needs flag, credentials, and approval.
- `PUBLIC_SEARCH_DISABLED`: public KAD search is blocked.
- `LICENSED_PROVIDER_SANDBOX_DISABLED`: licensed sandbox provider contract exists but is blocked.
- `OFFICIAL_API_DISABLED`: official court API is disabled.
- `LICENSED_PROVIDER_API_DISABLED`: licensed provider production mode is disabled.
- `PRODUCTION_DISABLED`: production mode is explicitly disabled.

Flags:

- `ENABLE_COURT_SANDBOX=false`
- `ENABLE_REAL_COURT_SEARCH=false`
- `ENABLE_PUBLIC_KAD_SEARCH=false`
- `ENABLE_COURT_SUBMISSION=false`

## General Rules

- `sandbox ready` does not mean `sandbox enabled`.
- Sandbox requires all of:
  - feature flag enabled;
  - sandbox credentials present in env/secrets;
  - active sandbox approval.
- Production flags stay `false` in this sprint.
- Backend blocks dangerous operations when flags or approvals are missing.
- Frontend shows mode and flag state, but never shows raw credentials.

## What Is Now Allowed

- sandbox test-connection with admin-only access;
- sandbox approval workflow for `SANDBOX` environment;
- sandbox readiness and credentials-presence checks;
- dry-run sandbox lookup, postal simulation, and court import simulation.

## What Is Still Forbidden

- production API calls;
- real postal sending;
- real court submission;
- public KAD scraping outside approved safe modes;
- exposing credentials in settings, logs, audit, exports, or frontend pages.
