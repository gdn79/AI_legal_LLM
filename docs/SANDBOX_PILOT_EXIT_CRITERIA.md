# SANDBOX PILOT EXIT CRITERIA

## Pass

- `safe-skipped` mode completes without crashes
- `dry-run` mode completes without production actions
- `live-sandbox` requires approval and credentials, or safe-skips when explicitly allowed
- dangerous operations remain blocked
- production API flags remain disabled
- no secrets leak to logs, frontend, exports, or reports
- sandbox pilot metrics and report are generated

## Pass With Issues

- live sandbox execution is skipped because credentials are absent
- framework remains safe and fully blocked from production actions
- only documentation or environment readiness issues remain

## Fail

- production API becomes enabled
- real postal send is possible
- court submission is possible
- approval gate is bypassed
- missing credentials crash the pilot
- credentials appear in frontend, logs, exports, or reports
