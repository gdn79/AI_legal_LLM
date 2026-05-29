# Real API Enablement Process

## Scope

This document is for future enablement only. Real APIs stay disabled in the current sprint.

## Who Can Enable

- Tech Lead or explicitly delegated integration owner.
- Separate legal and security approval is required.

## Required Inputs

- legal basis for API use;
- vendor documentation;
- sandbox credentials;
- rollout and rollback plan;
- approved feature-flag change.

## Mandatory Checks Before Any Real Enablement

- sandbox test-connection passes;
- dry-run checks pass;
- backend, frontend, and E2E suites pass;
- secrets policy is verified;
- audit and integration logs are reviewed;
- proof-of-service and authority gates remain intact.

## Feature Flags

The following stay `false` unless separately approved:

- `ENABLE_REAL_FNS`
- `ENABLE_REAL_POST_SEND`
- `ENABLE_REAL_COURT_SEARCH`
- `ENABLE_PUBLIC_KAD_SEARCH`
- `ENABLE_COURT_SUBMISSION`

## Rollback

- turn real flags back to `false`;
- revert mode to mock/manual/disabled;
- verify `/api/system/status`;
- verify `/api/integration-readiness/sandbox`.

## Explicitly Forbidden

- enabling real APIs without approval;
- using production credentials in dev/demo/pilot;
- real postal sending from demo or sandbox prep;
- real court submission in MVP;
- unsafe scraping or cookie-based bypasses for KAD.
