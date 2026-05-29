# SANDBOX CREDENTIALS REQUEST

## Requested Access

- FNS sandbox or test access
- Russian Post sandbox or test access
- Court provider sandbox or licensed test access

## Required Metadata

- responsible owner
- legal basis for access
- allowed scope of operations
- test-only limitations
- provider rate limits
- credential validity period
- rotation and revocation process

## Storage Rules

- credentials must be stored only in env or secret storage
- credentials must never be committed to git
- frontend must only see masked presence status
- audit and integration logs must never store raw credential values

## Operational Limits

- production flags remain disabled
- real letters are not sent
- court submission stays disabled
- public KAD scraping remains forbidden
- dangerous operations remain dry-run only
