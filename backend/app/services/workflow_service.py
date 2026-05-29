from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import CaseStatus, Claim, Pretension, RoleName, User, WorkflowEvent
from app.services.authority_service import AuthorityService
from app.services.postal_dispatch_service import PostalDispatchService


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def approve_pretension(self, pretension: Pretension, current_user: User):
        if current_user.role.name != RoleName.lawyer.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only lawyer can approve pretension")
        AuthorityService(self.db).ensure_case_signatory_has_authority(pretension.case, document_kind="pretension")
        pretension.approved = True
        self.db.add(WorkflowEvent(case_id=pretension.case_id, from_status=pretension.case.status, to_status=CaseStatus.PRETENSION_APPROVED.value, actor_user_id=current_user.id, comment="Pretension approved"))
        pretension.case.status = CaseStatus.PRETENSION_APPROVED.value
        self.db.add(pretension)
        self.db.commit()
        self.db.refresh(pretension)
        return pretension

    def approve_claim(self, claim: Claim, current_user: User):
        if current_user.role.name != RoleName.lawyer.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only lawyer can approve claim")
        AuthorityService(self.db).ensure_case_signatory_has_authority(claim.case, document_kind="claim")
        self.db.add(WorkflowEvent(case_id=claim.case_id, from_status=claim.case.status, to_status=CaseStatus.APPROVED_BY_LAWYER.value, actor_user_id=current_user.id, comment="Claim approved"))
        claim.approved = True
        claim.case.status = CaseStatus.APPROVED_BY_LAWYER.value
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def mark_court_package_ready(self, claim: Claim, current_user: User):
        if current_user.role.name not in {RoleName.lawyer.value, RoleName.admin.value}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only lawyer or admin can prepare the court package")
        self._ensure_court_package_requirements(claim)
        if claim.case.status == CaseStatus.COURT_PACKAGE_READY.value:
            return claim.case
        self.db.add(
            WorkflowEvent(
                case_id=claim.case_id,
                from_status=claim.case.status,
                to_status=CaseStatus.COURT_PACKAGE_READY.value,
                actor_user_id=current_user.id,
                comment="Court package readiness confirmed",
            )
        )
        claim.case.status = CaseStatus.COURT_PACKAGE_READY.value
        self.db.add(claim.case)
        self.db.commit()
        self.db.refresh(claim.case)
        return claim.case

    def _ensure_court_package_requirements(self, claim: Claim) -> None:
        case = claim.case
        if not claim.approved:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя сформировать судебный комплект: иск не утвержден.")
        if case.plaintiff_organization_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя сформировать судебный комплект: не выбрана организация-истец.")
        if case.signatory_id is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя сформировать судебный комплект: не выбран подписант.")
        AuthorityService(self.db).ensure_case_signatory_has_authority(case, document_kind="claim")
        if not (claim.content or "").strip():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя сформировать судебный комплект: отсутствует файл иска.")
        if case.claim_amount is None or float(case.claim_amount) <= 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Нельзя сформировать судебный комплект: отсутствует расчет требований.")
        if not PostalDispatchService(self.db).has_valid_claim_copy_proof(case.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя сформировать судебный комплект: отсутствует доказательство направления копии иска ответчику.",
            )
