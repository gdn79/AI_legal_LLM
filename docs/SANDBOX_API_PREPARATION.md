# Sandbox API Preparation

## Goal

Prepare safe sandbox wiring for:

- FNS / EGRUL source
- Russian Post sandbox or test mode
- Court import sandbox or licensed sandbox preparation

Production APIs remain disabled.

## Sandbox Ready Means

- adapter contract exists;
- feature flag exists and defaults to `false`;
- credentials are expected via env only;
- approval is required before enablement;
- test-connection is safe;
- dangerous operations stay dry-run or disabled.

## Required Env

- `ENABLE_FNS_SANDBOX`
- `ENABLE_RUSSIAN_POST_SANDBOX`
- `ENABLE_COURT_SANDBOX`
- sandbox credentials for the relevant provider

## Required Tests

- backend unit and integration tests
- frontend smoke tests
- E2E regression
- secret leakage checks
- idempotency checks
- dry-run checks

## Prohibited

- enabling production providers;
- sending real letters;
- submitting documents to court;
- committing credentials;
- weakening proof or authority gates.

## What Is Now Allowed

- sandbox dry-run test connection;
- sandbox readiness check;
- sandbox approval request, approval review, and revocation;
- sandbox-safe lookup, create-letter, send simulation, and import simulation;
- credentials presence checks with masked settings only.

## What Is Still Forbidden

- production API enablement;
- real postal sending;
- real court submission;
- public KAD scraping;
- any credential leakage to logs, audit, export, or frontend.
