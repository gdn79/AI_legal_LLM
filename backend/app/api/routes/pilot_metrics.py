from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.pilot_metrics import PilotCaseMetricsRead, PilotMetricsSummaryRead, PilotReportRead, PilotTimelineSummaryRead
from app.services.pilot_timeline_service import PilotTimelineService
from app.services.pilot_metrics_service import PilotMetricsService

router = APIRouter(tags=["pilot-metrics"])


@router.get("/pilot-metrics/summary", response_model=PilotMetricsSummaryRead)
def get_pilot_metrics_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(require_role(RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    return PilotMetricsService(db).summary(current_user, date_from=date_from, date_to=date_to)


@router.get("/pilot-metrics/cases/{case_id}", response_model=PilotCaseMetricsRead)
def get_case_metrics(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    return PilotMetricsService(db).case_metrics(case_id, current_user)


@router.get("/pilot-metrics/cases/{case_id}/timeline", response_model=PilotTimelineSummaryRead)
def get_case_timeline(
    case_id: int,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(require_role(RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    return PilotTimelineSummaryRead(
        case_id=case_id,
        timeline=PilotTimelineService(db).list_case_timeline(case_id, current_user, date_from=date_from, date_to=date_to),
    )


@router.get("/pilot-metrics/export")
def export_metrics(
    export_format: str = Query(default="json", pattern="^(json|csv)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(require_role(RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    payload = PilotMetricsService(db).export(current_user, export_format, date_from=date_from, date_to=date_to)
    if export_format == "csv":
        return PlainTextResponse(payload, media_type="text/csv")
    return PlainTextResponse(payload, media_type="application/json")


@router.get("/pilot-report", response_model=PilotReportRead)
def get_pilot_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(require_role(RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    return PilotMetricsService(db).report(current_user, date_from=date_from, date_to=date_to)
