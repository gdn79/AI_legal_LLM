from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.services.pilot_metrics_service import PilotMetricsService  # noqa: E402


def build_markdown(report, *, include_feedback: bool, include_metrics: bool, include_timeline: bool) -> str:
    sections = [
        "# PILOT RESULTS REPORT",
        "",
        "## 1. Общий статус",
        "",
        f"- recommendation: `{report.recommendation}`",
        f"- period: `{report.period}`",
        f"- date_from: `{report.date_from}`",
        f"- date_to: `{report.date_to}`",
        "",
        "## 2. Summary",
        "",
        f"- total_cases: {report.total_cases}",
        f"- case_statuses: {report.case_statuses}",
        f"- exports_generated: {report.exports_generated}",
        f"- exported_case_ids: {report.exported_case_ids}",
        "",
    ]
    if include_metrics:
        sections.extend(
            [
                "## 3. Metrics",
                "",
                f"- average_pretension_draft_minutes: {report.average_pretension_draft_minutes}",
                f"- average_pretension_draft_data_status: {report.average_pretension_draft_data_status}",
                f"- average_claim_draft_minutes: {report.average_claim_draft_minutes}",
                f"- ai_rag_warnings: {report.ai_rag_warnings}",
                f"- authority_warnings: {report.authority_warnings}",
                f"- authority_invalids: {report.authority_invalids}",
                f"- authority_checks_total: {report.authority_checks_total}",
                f"- blocked_actions: {report.blocked_actions}",
                "",
            ]
        )
    if include_feedback:
        sections.extend(
            [
                "## 4. Feedback",
                "",
                f"- feedback_total: {report.feedback_total}",
                f"- feedback_by_severity_total: {report.feedback_by_severity_total}",
                f"- feedback_by_severity_unresolved: {report.feedback_by_severity_unresolved}",
                f"- unresolved_items: {report.unresolved_items}",
                "",
            ]
        )
    if include_timeline:
        sections.extend(
            [
                "## 5. Timeline Summary",
                "",
                f"- timeline_summary: {report.timeline_summary}",
                "",
            ]
        )
    return "\n".join(sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate pilot report for a period.")
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--format", choices=["markdown", "json"], required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--include-feedback", action="store_true")
    parser.add_argument("--include-metrics", action="store_true")
    parser.add_argument("--include-timeline", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    date_from = date.fromisoformat(args.date_from)
    date_to = date.fromisoformat(args.date_to)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with Session(engine) as db:
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is None:
            raise RuntimeError("Admin role is missing")
        admin = db.scalar(select(User).where(User.role_id == admin_role.id))
        if admin is None:
            raise RuntimeError("Admin user is missing")
        report = PilotMetricsService(db).report(admin, date_from=date_from, date_to=date_to)

    if args.format == "json":
        payload = report.model_dump_json(indent=2)
    else:
        payload = build_markdown(
            report,
            include_feedback=args.include_feedback or not any([args.include_feedback, args.include_metrics, args.include_timeline]),
            include_metrics=args.include_metrics or not any([args.include_feedback, args.include_metrics, args.include_timeline]),
            include_timeline=args.include_timeline or not any([args.include_feedback, args.include_metrics, args.include_timeline]),
        )
    output.write_text(payload, encoding="utf-8")
    print(f"Pilot report written to {output}")


if __name__ == "__main__":
    main()
