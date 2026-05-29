from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentVersion, RoleName, User
from app.services.case_service import CaseService


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    def list_for_case(self, case_id: int, current_user: User) -> list[Document]:
        case = CaseService(self.db).get_case(case_id, current_user)
        return self.db.query(Document).filter(Document.case_id == case.id).order_by(Document.created_at.desc()).all()

    def get_for_download(self, document_id: int, current_user: User) -> Document:
        document = self.db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        CaseService(self.db).get_case(document.case_id, current_user)
        path = Path(document.storage_path)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
        return document

    def get_for_update(self, document_id: int, current_user: User) -> Document:
        document = self.get_for_download(document_id, current_user)
        if document.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved documents cannot be modified",
            )
        return document

    def list_versions(self, document_id: int, current_user: User) -> list[DocumentVersion]:
        document = self.get_for_download(document_id, current_user)
        query = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version.desc())
        )
        return list(self.db.scalars(query))

    def get_next_version_number(self, document: Document) -> int:
        last_version = self.db.scalar(
            select(DocumentVersion.version)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version.desc())
            .limit(1)
        )
        return (last_version or 0) + 1

    def ensure_document_write_access(self, current_user: User) -> None:
        if current_user.role.name not in {RoleName.initiator.value, RoleName.lawyer.value, RoleName.admin.value}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
