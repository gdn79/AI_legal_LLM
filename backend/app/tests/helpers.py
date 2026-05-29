from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient


def build_docx_bytes(text: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>""",
        )
    return buffer.getvalue()


def build_xlsx_bytes(text: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>{text}</t></si>
</sst>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c></row>
  </sheetData>
</worksheet>""",
        )
    return buffer.getvalue()


def build_pdf_bytes(text: str) -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Length 44 >> stream\nBT /F1 12 Tf 72 712 Td ("
        + text.encode("latin-1", errors="ignore")
        + b") Tj ET\nendstream\nendobj\ntrailer <<>>\n%%EOF"
    )


def create_case(client: TestClient, headers: dict[str, str], *, assigned_lawyer_id: int | None = None) -> int:
    payload = {
        "title": "Debt recovery",
        "description": "Contract dispute",
        "claimant_name": "OOO Alpha",
        "respondent_name": "OOO Beta",
        "claim_amount": 100000.0,
        "assigned_lawyer_id": assigned_lawyer_id,
    }
    response = client.post("/api/cases", headers=headers, json=payload)
    assert response.status_code == 200
    return response.json()["id"]


def upload_document_from_path(client: TestClient, case_id: int, headers: dict[str, str], path: Path, content_type: str):
    return client.post(
        f"/api/documents/{case_id}",
        headers=headers,
        files={"file": (path.name, path.read_bytes(), content_type)},
    )


def create_organization(client: TestClient, headers: dict[str, str], inn: str = "7701234567") -> int:
    response = client.post("/api/organizations", headers=headers, json={"inn": inn})
    assert response.status_code == 200
    return response.json()["id"]


def create_employee(
    client: TestClient,
    organization_id: int,
    headers: dict[str, str],
    *,
    full_name: str = "Петров Сотрудник",
    position: str = "Юрист",
    email: str = "employee@example.com",
    user_id: int | None = None,
) -> int:
    response = client.post(
        f"/api/organizations/{organization_id}/employees",
        headers=headers,
        json={"full_name": full_name, "position": position, "email": email, "user_id": user_id},
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_signatory(
    client: TestClient,
    organization_id: int,
    headers: dict[str, str],
    *,
    signatory_type: str,
    employee_id: int | None = None,
) -> int:
    response = client.post(
        f"/api/organizations/{organization_id}/signatories",
        headers=headers,
        json={"signatory_type": signatory_type, "employee_id": employee_id},
    )
    assert response.status_code == 200
    return response.json()["id"]


def assign_representation(
    client: TestClient,
    case_id: int,
    headers: dict[str, str],
    *,
    organization_id: int,
    signatory_id: int,
):
    response = client.patch(
        f"/api/cases/{case_id}/representation",
        headers=headers,
        json={"plaintiff_organization_id": organization_id, "signatory_id": signatory_id},
    )
    assert response.status_code == 200
    return response.json()


def create_power_of_attorney(
    client: TestClient,
    employee_id: int,
    headers: dict[str, str],
    *,
    number: str = "POA-1",
    issued_at: str = "2026-05-01",
    expires_at: str = "2026-12-31",
    authority_scope: str = "SIGN_PRETENSION,SIGN_CLAIM,REPRESENT_IN_COURT",
):
    response = client.post(
        f"/api/employees/{employee_id}/powers-of-attorney",
        headers=headers,
        data={
            "number": number,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "authority_scope": authority_scope,
        },
        files={"file": ("poa.pdf", b"power-of-attorney", "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_postal_dispatch(
    client: TestClient,
    headers: dict[str, str],
    *,
    case_id: int,
    organization_id: int,
    dispatch_kind: str = "claim_copy",
    recipient_name: str = "ООО Ответчик",
    recipient_address: str = "Москва, ул. Пример, д. 1",
) -> int:
    response = client.post(
        "/api/postal-dispatches",
        headers=headers,
        json={
            "case_id": case_id,
            "organization_id": organization_id,
            "dispatch_kind": dispatch_kind,
            "recipient_name": recipient_name,
            "recipient_address": recipient_address,
            "provider_mode": "MOCK_FOR_DEV",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def upload_postal_proof(
    client: TestClient,
    headers: dict[str, str],
    *,
    dispatch_id: int,
    proof_type: str = "claim_copy_dispatch_receipt",
):
    response = client.post(
        f"/api/russian-post/dispatches/{dispatch_id}/proofs",
        headers=headers,
        data={"proof_type": proof_type},
        files={"file": ("proof.pdf", b"postal-proof", "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["id"]


def refresh_postal_dispatch_status(client: TestClient, headers: dict[str, str], *, dispatch_id: int):
    response = client.post(f"/api/russian-post/dispatches/{dispatch_id}/status", headers=headers)
    assert response.status_code == 200
    return response.json()
