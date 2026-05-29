from __future__ import annotations

import hashlib

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import CaseStatus, Document, DocumentVersion, User
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.document_processing_service import DocumentProcessingService
from app.services.document_service import DocumentService
from app.services.storage_service import LocalStorageService


class DocumentPipelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = LocalStorageService()
        self.processing = DocumentProcessingService()
        self.documents = DocumentService(db)
        self.cases = CaseService(db)
        self.audit = AuditService(AuditRepository(db))

    async def create_document(
        self,
        *,
        case_id: int,
        upload: UploadFile,
        current_user: User,
        request_id: str,
    ) -> Document:
        self.documents.ensure_document_write_access(current_user)
        case = self.cases.get_case(case_id, current_user)
        stored = await self.storage.save_case_file(case.id, upload)
        extracted_text = self.processing.extract_text(
            filename=stored["filename"],
            content_type=stored["content_type"],
            payload=stored["payload"],
        )
        document = Document(
            case_id=case.id,
            filename=stored["filename"],
            content_type=stored["content_type"],
            storage_path=stored["storage_path"],
            sha256=self._sha256(stored["payload"]),
            extracted_text=extracted_text,
        )
        self.db.add(document)
        self.db.flush()
        self.db.add(
            DocumentVersion(
                document_id=document.id,
                version=1,
                storage_path=stored["storage_path"],
                sha256=self._sha256(stored["payload"]),
                extracted_text=extracted_text,
            )
        )
        case.status = CaseStatus.DOCUMENTS_UPLOADED.value
        self.db.add(case)
        self.db.commit()
        self.db.refresh(document)
        self.audit.log(
            current_user.id,
            "document_uploaded",
            "document",
            str(document.id),
            document.filename,
            request_id,
        )
        return document

    async def create_new_version(
        self,
        *,
        document_id: int,
        upload: UploadFile,
        current_user: User,
        request_id: str,
    ) -> Document:
        self.documents.ensure_document_write_access(current_user)
        document = self.documents.get_for_update(document_id, current_user)
        case = self.cases.get_case(document.case_id, current_user)
        next_version = self.documents.get_next_version_number(document)
        stored = await self.storage.save_document_version_file(case.id, document.filename, next_version, upload)
        extracted_text = self.processing.extract_text(
            filename=stored["filename"],
            content_type=stored["content_type"],
            payload=stored["payload"],
        )
        document.filename = stored["filename"]
        document.content_type = stored["content_type"]
        document.storage_path = stored["storage_path"]
        document.sha256 = self._sha256(stored["payload"])
        document.extracted_text = extracted_text
        self.db.add(document)
        self.db.add(
            DocumentVersion(
                document_id=document.id,
                version=next_version,
                storage_path=stored["storage_path"],
                sha256=self._sha256(stored["payload"]),
                extracted_text=extracted_text,
            )
        )
        self.db.commit()
        self.db.refresh(document)
        self.audit.log(
            current_user.id,
            "document_version_uploaded",
            "document",
            str(document.id),
            f"{document.filename}:v{next_version}",
            request_id,
        )
        return document

    @staticmethod
    def _sha256(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()
