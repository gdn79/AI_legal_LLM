from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.integrations.russian_post_adapter import get_russian_post_adapter
from app.models import Case, Organization, PostalDispatch, PostalDispatchStatus, PostalProofDocument, User
from app.services.integration_service import integration_http_error
from app.services.sandbox_service import SandboxService
from app.services.storage_service import LocalStorageService

VALID_CLAIM_COPY_PROOF_TYPES = {
    "claim_copy_dispatch_receipt",
    "claim_copy_delivery_receipt",
    "claim_copy_inventory",
}


class PostalDispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.storage = LocalStorageService()

    def create_dispatch(
        self,
        *,
        case_id: int,
        organization_id: int,
        dispatch_kind: str,
        recipient_name: str,
        recipient_address: str,
        provider_mode: str | None,
        idempotency_key: str | None = None,
        current_user: User,
    ) -> PostalDispatch:
        case = self.db.get(Case, case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        organization = self.db.get(Organization, organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        mode = provider_mode or self.settings.russian_post_mode
        sandbox = SandboxService(self.db)
        if mode == "RUSSIAN_POST_SANDBOX_READY":
            if not self.settings.enable_russian_post_sandbox:
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="russian_post",
                    operation="create_dispatch",
                    provider=self.settings.russian_post_provider,
                    mode=mode,
                    error_code="POST_SANDBOX_DISABLED",
                    safe_message="Russian Post sandbox is disabled by feature flag.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"enable_russian_post_sandbox": self.settings.enable_russian_post_sandbox},
                )
            if not sandbox.credentials_present("russian_post"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="russian_post",
                    operation="create_dispatch",
                    provider=self.settings.russian_post_provider,
                    mode=mode,
                    error_code="POST_SANDBOX_CREDENTIALS_MISSING",
                    safe_message="Russian Post sandbox credentials are not configured.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"credentials_present": False},
                )
            if not sandbox.has_active_approval("russian_post"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="russian_post",
                    operation="create_dispatch",
                    provider=self.settings.russian_post_provider,
                    mode=mode,
                    error_code="POST_SANDBOX_APPROVAL_REQUIRED",
                    safe_message="Russian Post sandbox approval is required before sandbox dispatch creation.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"approval_status": sandbox.approval_status("russian_post")},
                )
        normalized_key = (idempotency_key or "").strip()
        if mode == "RUSSIAN_POST_SANDBOX_READY" and not normalized_key:
            raise integration_http_error(
                status_code=status.HTTP_409_CONFLICT,
                integration_name="russian_post",
                operation="create_dispatch",
                provider=self.settings.russian_post_provider,
                mode=mode,
                error_code="POST_IDEMPOTENCY_KEY_REQUIRED",
                safe_message="Sandbox dispatch creation requires idempotency_key.",
                retryable=False,
                manual_action_required=True,
                details_safe_json={"idempotency_required": True},
            )
        if normalized_key:
            existing = self.db.scalar(select(PostalDispatch).where(PostalDispatch.idempotency_key == normalized_key))
            if existing is not None:
                return existing
        adapter = get_russian_post_adapter(mode)
        adapter_result = adapter.create_dispatch(
            case_id=case.id,
            organization_name=organization.short_name or organization.full_name or organization.inn,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            dispatch_kind=dispatch_kind,
        )
        dispatch = PostalDispatch(
            case_id=case.id,
            organization_id=organization.id,
            dispatch_kind=dispatch_kind,
            provider_mode=mode,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
            status=adapter_result["status"],
            tracking_number=adapter_result.get("tracking_number", ""),
            external_dispatch_id=adapter_result.get("external_dispatch_id", ""),
            source=adapter_result.get("source", mode),
            idempotency_key=normalized_key,
            status_payload=json.dumps(adapter_result.get("status_payload", {}), ensure_ascii=False),
            created_by_id=current_user.id,
            sent_at=datetime.now(UTC),
        )
        self.db.add(dispatch)
        self.db.commit()
        self.db.refresh(dispatch)
        return dispatch

    def dry_run_send(self, dispatch_id: int) -> dict:
        dispatch = self.get_dispatch(dispatch_id)
        errors: list[str] = []
        warnings: list[str] = []
        if not dispatch.recipient_address.strip():
            errors.append("recipient_address_missing")
        if not dispatch.recipient_name.strip():
            errors.append("recipient_name_missing")
        if dispatch.case.claim is None or not dispatch.case.claim.approved:
            warnings.append("approved_claim_not_found_for_dispatch_context")
        if dispatch.dispatch_kind == "claim_copy" and not dispatch.case.claim:
            errors.append("claim_document_missing")
        return {
            "operation": "send_postal_dispatch",
            "dry_run": True,
            "ready": not errors,
            "warnings": warnings,
            "errors": errors,
            "safe_preview_json": {
                "dispatch_id": dispatch.id,
                "dispatch_kind": dispatch.dispatch_kind,
                "provider_mode": dispatch.provider_mode,
                "recipient_name": dispatch.recipient_name,
                "tracking_number": dispatch.tracking_number or None,
            },
        }

    def normalize_address(self, address: str, *, sandbox: bool = False) -> dict:
        mode = "RUSSIAN_POST_SANDBOX_READY" if sandbox else self.settings.russian_post_mode
        sandbox_service = SandboxService(self.db)
        if mode == "RUSSIAN_POST_SANDBOX_READY":
            if not self.settings.enable_russian_post_sandbox:
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="russian_post",
                    operation="normalize_address",
                    provider=self.settings.russian_post_provider,
                    mode=mode,
                    error_code="POST_SANDBOX_DISABLED",
                    safe_message="Russian Post sandbox is disabled by feature flag.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"enable_russian_post_sandbox": self.settings.enable_russian_post_sandbox},
                )
            if not sandbox_service.credentials_present("russian_post"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="russian_post",
                    operation="normalize_address",
                    provider=self.settings.russian_post_provider,
                    mode=mode,
                    error_code="POST_SANDBOX_CREDENTIALS_MISSING",
                    safe_message="Russian Post sandbox credentials are not configured.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"credentials_present": False},
                )
            if not sandbox_service.has_active_approval("russian_post"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="russian_post",
                    operation="normalize_address",
                    provider=self.settings.russian_post_provider,
                    mode=mode,
                    error_code="POST_SANDBOX_APPROVAL_REQUIRED",
                    safe_message="Russian Post sandbox approval is required before address normalization.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"approval_status": sandbox_service.approval_status("russian_post")},
                )
        adapter = get_russian_post_adapter(mode)
        if hasattr(adapter, "normalize_address"):
            return adapter.normalize_address(address)
        return {
            "normalized_address": address.strip(),
            "status": "manual_required",
            "source": mode,
        }

    def send_dispatch(self, dispatch_id: int, *, dry_run: bool) -> dict:
        dispatch = self.get_dispatch(dispatch_id)
        if dispatch.provider_mode == "RUSSIAN_POST_SANDBOX_READY" and not dry_run:
            raise integration_http_error(
                status_code=status.HTTP_409_CONFLICT,
                integration_name="russian_post",
                operation="send_dispatch",
                provider=self.settings.russian_post_provider,
                mode=dispatch.provider_mode,
                error_code="POST_SANDBOX_DRY_RUN_REQUIRED",
                safe_message="Russian Post sandbox send is allowed only in dry_run mode.",
                retryable=False,
                manual_action_required=True,
                details_safe_json={"dry_run_required": True},
            )
        if dry_run:
            return self.dry_run_send(dispatch_id)
        raise integration_http_error(
            status_code=status.HTTP_409_CONFLICT,
            integration_name="russian_post",
            operation="send_dispatch",
            provider=self.settings.russian_post_provider,
            mode=self.settings.russian_post_mode,
            error_code="POST_SEND_DISABLED",
            safe_message="Real Russian Post send is disabled. Use dry_run or manual/mock modes.",
            retryable=False,
            manual_action_required=True,
            details_safe_json={"enable_real_post_send": self.settings.enable_real_post_send},
        )

    def list_dispatches(self, case_id: int | None = None) -> list[PostalDispatch]:
        query = (
            select(PostalDispatch)
            .options(selectinload(PostalDispatch.proof_documents))
            .order_by(PostalDispatch.created_at.desc())
        )
        if case_id is not None:
            query = query.where(PostalDispatch.case_id == case_id)
        return list(self.db.scalars(query))

    def get_dispatch(self, dispatch_id: int) -> PostalDispatch:
        dispatch = self.db.scalar(
            select(PostalDispatch)
            .options(selectinload(PostalDispatch.proof_documents))
            .where(PostalDispatch.id == dispatch_id)
        )
        if dispatch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Postal dispatch not found")
        return dispatch

    def refresh_status(self, dispatch_id: int) -> PostalDispatch:
        dispatch = self.get_dispatch(dispatch_id)
        adapter = get_russian_post_adapter(dispatch.provider_mode)
        adapter_result = adapter.refresh_status(
            external_dispatch_id=dispatch.external_dispatch_id or None,
            tracking_number=dispatch.tracking_number or None,
        )
        dispatch.status = adapter_result["status"]
        dispatch.status_payload = json.dumps(adapter_result.get("status_payload", {}), ensure_ascii=False)
        dispatch.source = adapter_result.get("source", dispatch.source)
        if dispatch.status == PostalDispatchStatus.DELIVERED.value:
            dispatch.delivered_at = datetime.now(UTC)
        self.db.add(dispatch)
        self.db.commit()
        self.db.refresh(dispatch)
        return dispatch

    def upload_proof(
        self,
        *,
        dispatch_id: int,
        proof_type: str,
        file_name: str,
        file_bytes: bytes,
        current_user: User,
    ) -> PostalProofDocument:
        dispatch = self.get_dispatch(dispatch_id)
        file_path = self.storage.save_bytes(
            subdir=f"case_{dispatch.case_id}/postal_proofs",
            filename=file_name,
            payload=file_bytes,
        )
        proof = PostalProofDocument(
            postal_dispatch_id=dispatch.id,
            file_name=file_name,
            file_path=file_path,
            proof_type=proof_type,
            source=dispatch.provider_mode,
            created_by_id=current_user.id,
        )
        self.db.add(proof)
        self.db.commit()
        self.db.refresh(proof)
        return proof

    def has_claim_copy_proof(self, case_id: int) -> bool:
        return self.has_valid_claim_copy_proof(case_id)

    def has_valid_claim_copy_proof(self, case_id: int) -> bool:
        dispatches = list(
            self.db.scalars(
                select(PostalDispatch)
                .options(selectinload(PostalDispatch.proof_documents))
                .where(PostalDispatch.case_id == case_id, PostalDispatch.dispatch_kind == "claim_copy")
            )
        )
        return any(self._is_valid_claim_copy_dispatch(dispatch) for dispatch in dispatches)

    def _is_valid_claim_copy_dispatch(self, dispatch: PostalDispatch) -> bool:
        if dispatch.status not in {PostalDispatchStatus.SENT.value, PostalDispatchStatus.DELIVERED.value}:
            return False
        return any(proof.proof_type in VALID_CLAIM_COPY_PROOF_TYPES and bool(proof.file_path) for proof in dispatch.proof_documents)
