# Sandbox Approval Process

## Request

- Integration owner requests sandbox enablement.
- Request includes provider name, environment, purpose, and expiry date.

## Approval

- Approval is recorded as `IntegrationApproval`.
- Status must be `APPROVED`.
- Expired approvals are treated as inactive.

## Revocation

- Approval may be marked `REVOKED` or `REJECTED`.
- Expired approvals become `EXPIRED`.

## Audit

- Every approval change must be auditable.
- Approval does not expose credentials.

## Important

- Sandbox flag alone is not enough.
- Sandbox credentials alone are not enough.
- Active approval is mandatory before sandbox provider enablement.
- Production approval requests may be recorded, but they remain blocked and cannot enable production providers in the current sprint.
