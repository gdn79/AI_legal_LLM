from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


class OCRHookService:
    def extract_text(self, *, filename: str, payload: bytes) -> str:
        return f"OCR required for {Path(filename).name}"


class DocumentProcessingService:
    def __init__(self, ocr_hook: OCRHookService | None = None) -> None:
        self.ocr_hook = ocr_hook or OCRHookService()

    def extract_text(self, *, filename: str, content_type: str, payload: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if content_type == "text/plain" or suffix == ".txt":
            return self._extract_txt(payload)
        if content_type == "application/pdf" or suffix == ".pdf":
            parsed = self._extract_pdf(payload)
            return parsed or self.ocr_hook.extract_text(filename=filename, payload=payload)
        if (
            content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or suffix == ".docx"
        ):
            return self._extract_docx(payload)
        if (
            content_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            or suffix == ".xlsx"
        ):
            return self._extract_xlsx(payload)
        if content_type in {"image/png", "image/jpeg"} or suffix in {".png", ".jpg", ".jpeg"}:
            return self.ocr_hook.extract_text(filename=filename, payload=payload)
        return payload.decode("utf-8", errors="ignore").strip()[:10000]

    def _extract_txt(self, payload: bytes) -> str:
        return payload.decode("utf-8", errors="ignore").strip()[:10000]

    def _extract_pdf(self, payload: bytes) -> str:
        decoded = payload.decode("latin-1", errors="ignore")
        matches = re.findall(r"\((.*?)\)\s*Tj", decoded, flags=re.DOTALL)
        cleaned = " ".join(self._cleanup_pdf_token(token) for token in matches if token)
        return cleaned.strip()[:10000]

    def _cleanup_pdf_token(self, token: str) -> str:
        token = token.replace("\\(", "(").replace("\\)", ")").replace("\\n", " ").replace("\\r", " ")
        return re.sub(r"\s+", " ", token).strip()

    def _extract_docx(self, payload: bytes) -> str:
        try:
            with ZipFile(BytesIO(payload)) as archive:
                xml_payload = archive.read("word/document.xml")
        except (BadZipFile, KeyError):
            return ""
        root = ElementTree.fromstring(xml_payload)
        chunks = [node.text.strip() for node in root.iter() if self._tag_name(node.tag) == "t" and node.text and node.text.strip()]
        return " ".join(chunks)[:10000]

    def _extract_xlsx(self, payload: bytes) -> str:
        try:
            with ZipFile(BytesIO(payload)) as archive:
                shared_strings = self._read_shared_strings(archive)
                chunks: list[str] = []
                for name in archive.namelist():
                    if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                        chunks.extend(self._read_sheet_cells(archive.read(name), shared_strings))
        except BadZipFile:
            return ""
        return " ".join(chunk for chunk in chunks if chunk).strip()[:10000]

    def _read_shared_strings(self, archive: ZipFile) -> list[str]:
        try:
            xml_payload = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        try:
            root = ElementTree.fromstring(xml_payload)
            values = [item.text.strip() for item in root.iter() if self._tag_name(item.tag) == "t" and item.text]
            if values:
                return values
        except ElementTree.ParseError:
            pass
        decoded = xml_payload.decode("utf-8", errors="ignore")
        return [match.strip() for match in re.findall(r"<[^>]*t[^>]*>(.*?)</[^>]*t>", decoded, flags=re.DOTALL)]

    def _read_sheet_cells(self, xml_payload: bytes, shared_strings: list[str]) -> list[str]:
        values: list[str] = []
        try:
            root = ElementTree.fromstring(xml_payload)
            for cell in root.iter():
                if self._tag_name(cell.tag) != "c":
                    continue
                cell_type = cell.attrib.get("t")
                value_node = next((node for node in cell if self._tag_name(node.tag) == "v" and node.text), None)
                if value_node is None or not value_node.text:
                    continue
                if cell_type == "s":
                    index = int(value_node.text)
                    if 0 <= index < len(shared_strings):
                        values.append(shared_strings[index])
                else:
                    values.append(value_node.text.strip())
        except ElementTree.ParseError:
            values = []
        if values:
            return values

        decoded = xml_payload.decode("utf-8", errors="ignore")
        shared_matches = re.findall(r'<c[^>]*t="s"[^>]*>.*?<v>(\d+)</v>.*?</c>', decoded, flags=re.DOTALL)
        for match in shared_matches:
            index = int(match)
            if 0 <= index < len(shared_strings):
                values.append(shared_strings[index])
        raw_matches = re.findall(r'<c(?![^>]*t="s")[^>]*>.*?<v>(.*?)</v>.*?</c>', decoded, flags=re.DOTALL)
        values.extend(match.strip() for match in raw_matches if match.strip())
        return values

    def _tag_name(self, tag: str) -> str:
        return tag.rsplit("}", maxsplit=1)[-1]
