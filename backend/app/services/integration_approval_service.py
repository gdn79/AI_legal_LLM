from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IntegrationApproval, IntegrationApprovalEnvironment, IntegrationApprovalStatus, User


INTEGRATION_NAME_MAP = {
    "fns": "FNS",
    "FNS": "FNS",
    "russian_post": "RUSSIAN_POST",
    "RUSSIAN_POST": "RUSSIAN_POST",
    "court": "COURT_ARBITR",
    "court_arbitr": "COURT_ARBITR",
    "COURT_ARBITR": "COURT_ARBITR",
}


class IntegrationApprovalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def normalize_integration_name(self, integration_name: str) -> str:
        normalized = INTEGRATION_NAME_MAP.get(integration_name.strip())
        if normalized is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported integration_name. Expected FNS, RUSSIAN_POST, or COURT_ARBITR.",
            )
        return normalized

    @staticmethod
    def normalize_environment(environment: str) -> str:
        normalized = environment.strip().upper()
        allowed = {IntegrationApprovalEnvironment.SANDBOX.value, IntegrationApprovalEnvironment.PRODUCTION.value}
        if normalized not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported environment. Expected SANDBOX or PRODUCTION.",
            )
        return normalized

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def request_approval(
        self,
        *,
        integration_name: str,
        environment: str,
        reason: str,
        expires_at: datetime | None,
        requested_by: User,
    ) -> IntegrationApproval:
        integration_name = self.normalize_integration_name(integration_name)
        environment = self.normalize_environment(environment)
        expires_at = self._as_utc(expires_at)
        now = datetime.now(UTC)

        if environment == IntegrationApprovalEnvironment.SANDBOX.value:
            if expires_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sandbox approval request requires expires_at.",
                )
            if expires_at <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="expires_at must be in the future.",
                )
            approval = IntegrationApproval(
                integration_name=integration_name,
                environment=environment,
                requested_by_id=requested_by.id,
                status=IntegrationApprovalStatus.REQUESTED.value,
                reason=reason,
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
        else:
            approval = IntegrationApproval(
                integration_name=integration_name,
                environment=environment,
                requested_by_id=requested_by.id,
                status=IntegrationApprovalStatus.REJECTED.value,
                reason=reason or "Production approvals are disabled in the current MVP.",
                created_at=now,
                updated_at=now,
            )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def list_approvals(
        self,
        *,
        integration_name: str | None = None,
        environment: str | None = None,
        status_value: str | None = None,
    ) -> list[IntegrationApproval]:
        query = select(IntegrationApproval).order_by(IntegrationApproval.created_at.desc())
        if integration_name:
            query = query.where(
                IntegrationApproval.integration_name == self.normalize_integration_name(integration_name)
            )
        if environment:
            query = query.where(IntegrationApproval.environment == self.normalize_environment(environment))
        if status_value:
            query = query.where(IntegrationApproval.status == status_value.strip().upper())
        approvals = list(self.db.scalars(query).all())
        updated = False
        for approval in approvals:
            if self._expire_if_needed(approval):
                updated = True
        if updated:
            self.db.commit()
        return approvals

    def list_active(self) -> list[IntegrationApproval]:
        now = datetime.now(UTC)
        approvals = list(
            self.db.scalars(
                select(IntegrationApproval)
                .where(
                    IntegrationApproval.environment == IntegrationApprovalEnvironment.SANDBOX.value,
                    IntegrationApproval.status == IntegrationApprovalStatus.APPROVED.value,
                )
                .order_by(IntegrationApproval.created_at.desc())
            ).all()
        )
        active: list[IntegrationApproval] = []
        updated = False
        for approval in approvals:
            if self._expire_if_needed(approval):
                updated = True
                continue
            expires_at = self._as_utc(approval.expires_at)
            if expires_at is None or expires_at > now:
                active.append(approval)
        if updated:
            self.db.commit()
        return active

    def get_approval(self, approval_id: int) -> IntegrationApproval:
        approval = self.db.get(IntegrationApproval, approval_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration approval not found")
        if self._expire_if_needed(approval):
            self.db.commit()
            self.db.refresh(approval)
        return approval

    def approve(self, approval_id: int, *, approved_by: User, reason: str = "") -> IntegrationApproval:
        approval = self.get_approval(approval_id)
        if approval.environment == IntegrationApprovalEnvironment.PRODUCTION.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Production approval is disabled in the current MVP.",
            )
        if approval.expires_at is None or self._as_utc(approval.expires_at) <= datetime.now(UTC):
            approval.status = IntegrationApprovalStatus.EXPIRED.value
            approval.updated_at = datetime.now(UTC)
            self.db.add(approval)
            self.db.commit()
            self.db.refresh(approval)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval request is expired.")
        approval.status = IntegrationApprovalStatus.APPROVED.value
        approval.approved_by_id = approved_by.id
        approval.approved_at = datetime.now(UTC)
        approval.updated_at = datetime.now(UTC)
        if reason:
            approval.reason = reason
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def reject(self, approval_id: int, *, acted_by: User, reason: str = "") -> IntegrationApproval:
        approval = self.get_approval(approval_id)
        approval.status = IntegrationApprovalStatus.REJECTED.value
        approval.approved_by_id = acted_by.id
        approval.updated_at = datetime.now(UTC)
        if reason:
            approval.reason = reason
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def revoke(self, approval_id: int, *, acted_by: User, reason: str = "") -> IntegrationApproval:
        approval = self.get_approval(approval_id)
        approval.status = IntegrationApprovalStatus.REVOKED.value
        approval.approved_by_id = acted_by.id
        approval.updated_at = datetime.now(UTC)
        if reason:
            approval.reason = reason
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def _expire_if_needed(self, approval: IntegrationApproval) -> bool:
        if approval.status != IntegrationApprovalStatus.APPROVED.value:
            return False
        expires_at = self._as_utc(approval.expires_at)
        if expires_at is None or expires_at > datetime.now(UTC):
            return False
        approval.status = IntegrationApprovalStatus.EXPIRED.value
        approval.updated_at = datetime.now(UTC)
        self.db.add(approval)
        return True
