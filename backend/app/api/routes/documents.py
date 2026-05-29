from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_id
from app.db.session import get_db
from app.models import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.document import DocumentRead, DocumentVersionRead
from app.services.audit_service import AuditService
from app.services.document_pipeline_service import DocumentPipelineService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/download/{document_id}")
def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    document = DocumentService(db).get_for_download(document_id, current_user)
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "document_downloaded",
        "document",
        str(document.id),
        document.filename,
        request_id,
    )
    return FileResponse(path=Path(document.storage_path), filename=document.filename, media_type=document.content_type)


@router.get("/item/{document_id}/versions", response_model=list[DocumentVersionRead])
def list_document_versions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return DocumentService(db).list_versions(document_id, current_user)


@router.post("/item/{document_id}/versions", response_model=DocumentRead)
async def upload_document_version(
    document_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    return await DocumentPipelineService(db).create_new_version(
        document_id=document_id,
        upload=file,
        current_user=current_user,
        request_id=request_id,
    )


@router.post("/{case_id}", response_model=DocumentRead)
async def upload_document(
    case_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    return await DocumentPipelineService(db).create_document(
        case_id=case_id,
        upload=file,
        current_user=current_user,
        request_id=request_id,
    )


@router.get("/{case_id}", response_model=list[DocumentRead])
def list_documents(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return DocumentService(db).list_for_case(case_id, current_user)
