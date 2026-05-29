from app.tests.helpers import (
    assign_representation,
    create_case,
    create_employee,
    create_organization,
    create_power_of_attorney,
    create_postal_dispatch,
    create_signatory,
    upload_postal_proof,
    upload_document_from_path,
)


def test_e2e_happy_path(client, auth_headers, sample_documents_dir):
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    manager_headers = auth_headers("manager")
    admin_headers = auth_headers("admin")

    organization_id = create_organization(client, admin_headers, inn="7701234570")
    employee_id = create_employee(client, organization_id, admin_headers)
    signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="AUTHORIZED_EMPLOYEE", employee_id=employee_id)
    create_power_of_attorney(client, employee_id, admin_headers)

    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=signatory_id)

    contract_upload = upload_document_from_path(
        client,
        case_id,
        initiator_headers,
        sample_documents_dir / "contract.txt",
        "text/plain",
    )
    assert contract_upload.status_code == 200

    act_upload = upload_document_from_path(
        client,
        case_id,
        initiator_headers,
        sample_documents_dir / "act.txt",
        "text/plain",
    )
    assert act_upload.status_code == 200

    source = client.post(
        "/api/rag/sources",
        headers=admin_headers,
        json={
            "title": "Debt recovery obligations",
            "source_type": "law",
            "category": "debt",
            "fragment": (sample_documents_dir / "legal_source.txt").read_text(encoding="utf-8"),
        },
    )
    assert source.status_code == 200

    import_job = client.post(
        "/api/court-import/jobs",
        headers=admin_headers,
        json={
            "organization_id": organization_id,
            "inn": "7701234570",
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "participation_role": "claimant",
            "provider_mode": "MOCK_FOR_DEV",
        },
    )
    assert import_job.status_code == 200
    imported_cases = client.get(f"/api/court-import/jobs/{import_job.json()['id']}/cases", headers=admin_headers)
    assert imported_cases.status_code == 200
    external_case_id = imported_cases.json()[0]["id"]

    extracted = client.post(f"/api/extraction/{case_id}/run", headers=initiator_headers)
    assert extracted.status_code == 200
    assert extracted.json()["facts"]

    pretension = client.post(f"/api/pretensions/{case_id}/generate", headers=lawyer_headers)
    assert pretension.status_code == 200
    assert pretension.json()["content"]

    pretension_approved = client.post(f"/api/workflow/{case_id}/approve-pretension", headers=lawyer_headers)
    assert pretension_approved.status_code == 200
    assert pretension_approved.json()["approved"] is True

    claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert claim.status_code == 200
    assert claim.json()["content"]

    rag_search = client.post(
        "/api/rag/search",
        headers=lawyer_headers,
        json={"query": "debt recovery", "case_id": case_id, "top_k": 3},
    )
    assert rag_search.status_code == 200
    assert rag_search.json()["results"]

    authority = client.post(
        f"/api/signatories/{signatory_id}/check-authority",
        headers=admin_headers,
        json={"case_id": case_id, "document_kind": "claim"},
    )
    assert authority.status_code == 200
    assert authority.json()["valid"] is True

    checklist = client.get(f"/api/checklists/{case_id}", headers=lawyer_headers)
    assert checklist.status_code == 200
    for item in checklist.json()["items"]:
        updated = client.put(
            f"/api/checklists/items/{item['id']}",
            headers=lawyer_headers,
            json={"is_completed": True, "notes": "happy-path complete"},
        )
        assert updated.status_code == 200
        assert updated.json()["is_completed"] is True

    claim_approved = client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)
    assert claim_approved.status_code == 200
    assert claim_approved.json()["approved"] is True

    dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refreshed_dispatch = client.post(f"/api/russian-post/dispatches/{dispatch_id}/status", headers=lawyer_headers)
    assert refreshed_dispatch.status_code == 200
    assert refreshed_dispatch.json()["status"] == "DELIVERED"

    upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)
    proof_check = client.get(f"/api/russian-post/cases/{case_id}/claim-copy-proof", headers=lawyer_headers)
    assert proof_check.status_code == 200
    assert proof_check.json()["has_claim_copy_proof"] is True

    linked = client.post(
        f"/api/external-court-cases/{external_case_id}/link",
        headers=admin_headers,
        json={"case_id": case_id},
    )
    assert linked.status_code == 200
    assert linked.json()["linked_case_id"] == case_id

    submission = client.post(
        "/api/court-submission",
        headers=lawyer_headers,
        json={"case_id": case_id, "external_court_case_id": external_case_id, "note": "manual filing package"},
    )
    assert submission.status_code == 200
    assert submission.json()["status"] == "READY_FOR_MANUAL_SUBMISSION"

    exported = client.post(f"/api/export/{case_id}", headers=lawyer_headers)
    assert exported.status_code == 200
    assert exported.json()["archive_path"].endswith(".zip")

    citations = client.get(f"/api/rag/citations/{case_id}", headers=lawyer_headers)
    assert citations.status_code == 200
    assert citations.json()

    audit = client.get("/api/audit", headers=admin_headers)
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()]
    assert "organization_created" in actions
    assert "employee_created" in actions
    assert "signatory_created" in actions
    assert "power_of_attorney_created" in actions
    assert "court_import_job_created" in actions
    assert "external_court_case_linked" in actions
    assert "case_created" in actions
    assert "case_representation_updated" in actions
    assert "document_uploaded" in actions
    assert "facts_extracted" in actions
    assert "pretension_generated" in actions
    assert "pretension_approved" in actions
    assert "claim_generated" in actions
    assert "claim_approved" in actions
    assert "postal_dispatch_created" in actions
    assert "postal_dispatch_status_updated" in actions
    assert "postal_proof_uploaded" in actions
    assert "court_submission_package_prepared" in actions
    assert "case_exported" in actions

    dashboard = client.get("/api/dashboard", headers=manager_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_cases"] >= 1
