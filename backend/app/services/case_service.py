from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, CaseStatus, Checklist, ChecklistItem, Claim, ClaimVersion, Organization, Party, Pretension, PretensionVersion, RoleName, Signatory, User, WorkflowEvent


class CaseService:
    def __init__(self, db: Session):
        self.db = db

    def create_case(self, *, current_user: User, data) -> Case:
        new_case = Case(
            title=data.title,
            description=data.description,
            claimant_name=data.claimant_name,
            respondent_name=data.respondent_name,
            claim_amount=data.claim_amount,
            created_by_id=current_user.id,
            assigned_lawyer_id=data.assigned_lawyer_id,
            plaintiff_organization_id=getattr(data, "plaintiff_organization_id", None),
            signatory_id=getattr(data, "signatory_id", None),
        )
        self._validate_representation(
            plaintiff_organization_id=new_case.plaintiff_organization_id,
            signatory_id=new_case.signatory_id,
        )
        self.db.add(new_case)
        self.db.flush()
        pretension = Pretension(case_id=new_case.id)
        claim = Claim(case_id=new_case.id)
        checklist = Checklist(case_id=new_case.id)
        self.db.add_all(
            [
                Party(case_id=new_case.id, role="claimant", name=data.claimant_name),
                Party(case_id=new_case.id, role="respondent", name=data.respondent_name),
                pretension,
                claim,
                checklist,
                WorkflowEvent(case_id=new_case.id, from_status="", to_status=CaseStatus.NEW.value, actor_user_id=current_user.id, comment="Case created"),
            ]
        )
        self.db.flush()
        self.db.add_all(
            [
                PretensionVersion(pretension_id=pretension.id, version=1, content="", is_approved_snapshot=False),
                ClaimVersion(claim_id=claim.id, version=1, content="", is_approved_snapshot=False),
                ChecklistItem(checklist_id=checklist.id, title="Проверить комплект документов"),
                ChecklistItem(checklist_id=checklist.id, title="Проверить доказательства направления претензии"),
                ChecklistItem(checklist_id=checklist.id, title="Проверить расчет требований"),
            ]
        )
        self.db.commit()
        self.db.refresh(new_case)
        return new_case

    def list_cases(self, current_user: User) -> list[Case]:
        query = select(Case).order_by(Case.created_at.desc())
        if current_user.role.name == RoleName.initiator.value:
            query = query.where(Case.created_by_id == current_user.id)
        elif current_user.role.name == RoleName.lawyer.value:
            query = query.where(Case.assigned_lawyer_id == current_user.id)
        return list(self.db.scalars(query))

    def get_case(self, case_id: int, current_user: User) -> Case:
        case = self.db.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if current_user.role.name in {RoleName.admin.value, RoleName.manager.value}:
            return case
        if current_user.role.name == RoleName.initiator.value and case.created_by_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if current_user.role.name == RoleName.lawyer.value and case.assigned_lawyer_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return case

    def update_status(self, case: Case, status_value: CaseStatus) -> Case:
        case.status = status_value.value
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def assign_representation(self, case: Case, *, plaintiff_organization_id: int, signatory_id: int) -> Case:
        self._validate_representation(
            plaintiff_organization_id=plaintiff_organization_id,
            signatory_id=signatory_id,
        )
        case.plaintiff_organization_id = plaintiff_organization_id
        case.signatory_id = signatory_id
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def _validate_representation(self, *, plaintiff_organization_id: int | None, signatory_id: int | None) -> None:
        if plaintiff_organization_id is None and signatory_id is None:
            return
        if plaintiff_organization_id is None or signatory_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization and signatory must be set together")
        organization = self.db.get(Organization, plaintiff_organization_id)
        signatory = self.db.get(Signatory, signatory_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        if signatory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signatory not found")
        if signatory.organization_id != organization.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signatory belongs to another organization")
