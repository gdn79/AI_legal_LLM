import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "text/plain",
    "message/rfc822",
    "application/zip",
}

BLOCKED_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".js",
    ".jse",
    ".msi",
    ".ps1",
    ".psm1",
    ".scr",
    ".vbs",
    ".wsf",
}


class LocalStorageService:
    def __init__(self) -> None:
        self.root = get_settings().storage_path
        self.root.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        cleaned = Path(filename).name
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned)
        return cleaned or "document.bin"

    def validate_filename(self, filename: str) -> str:
        safe_name = self.sanitize_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix in BLOCKED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Blocked file extension")
        return safe_name

    def save_bytes(self, *, subdir: str, filename: str, payload: bytes) -> str:
        safe_name = self.validate_filename(filename)
        target_dir = self.root / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / safe_name
        destination.write_bytes(payload)
        return str(destination)

    async def save_case_file(self, case_id: int, upload: UploadFile) -> dict[str, str | bytes]:
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

        safe_name = self.validate_filename(upload.filename or "document.bin")
        case_dir = self.root / f"case_{case_id}"
        case_dir.mkdir(parents=True, exist_ok=True)
        destination = case_dir / safe_name
        payload = await upload.read()
        destination.write_bytes(payload)
        return {
            "filename": safe_name,
            "content_type": upload.content_type or "application/octet-stream",
            "storage_path": str(destination),
            "payload": payload,
        }

    async def save_document_version_file(
        self,
        case_id: int,
        original_filename: str,
        version: int,
        upload: UploadFile,
    ) -> dict[str, str | bytes]:
        stored = await self.save_case_file(case_id, upload)
        filename = str(stored["filename"])
        base = Path(original_filename).stem or Path(filename).stem
        suffix = Path(filename).suffix or Path(original_filename).suffix or ".bin"
        versioned_name = self.sanitize_filename(f"{base}_v{version}{suffix}")
        case_dir = self.root / f"case_{case_id}"
        destination = case_dir / versioned_name
        if Path(stored["storage_path"]).resolve() != destination.resolve():
            destination.write_bytes(stored["payload"])
            Path(stored["storage_path"]).unlink(missing_ok=True)
        stored["filename"] = versioned_name
        stored["storage_path"] = str(destination)
        return stored
