# Sandbox Security Checklist

- Sandbox credentials are stored only in env or secret storage.
- Settings API returns masked sandbox values only.
- Audit log contains change fact only, never raw credentials.
- Integration request log contains safe metadata only.
- Frontend does not receive credentials.
- Export packages do not contain credentials.
- Dry-run stays mandatory for dangerous sandbox operations.
- Production flags remain disabled.
- Rollback to mock/manual mode is documented.
- Public KAD search and court submission remain blocked unless separately approved.
