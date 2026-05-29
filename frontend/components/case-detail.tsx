"use client";

import Link from "next/link";
import { useState } from "react";
import { apiClient } from "../lib/api-client";
import type { CaseDetailModel, CaseDocument, CaseFact, Checklist, DraftDocument } from "../lib/types";
import { canRole, useAuth } from "./providers";

export function CaseDetail({ caseData }: { caseData: CaseDetailModel }) {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<CaseDocument[]>(caseData.documents);
  const [facts, setFacts] = useState<CaseFact[]>(caseData.facts);
  const [pretension] = useState<DraftDocument | null>(caseData.pretension ?? null);
  const [claim] = useState<DraftDocument | null>(caseData.claim ?? null);
  const [checklist] = useState<Checklist | null>(caseData.checklist ?? null);
  const [status, setStatus] = useState(caseData.status);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadDocument = async (file: File | null) => {
    if (!file) return;
    setBusy("upload");
    setError(null);
    try {
      const uploaded = await apiClient.uploadDocument(caseData.id, file);
      setDocuments((current) => [uploaded, ...current]);
      setStatus("DOCUMENTS_UPLOADED");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить документ");
    } finally {
      setBusy(null);
    }
  };

  const runExtraction = async () => {
    setBusy("extract");
    setError(null);
    try {
      const result = await apiClient.runExtraction(caseData.id);
      setFacts(result.facts);
      setStatus(result.status as CaseDetailModel["status"]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось запустить извлечение фактов");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid two">
      <section className="card stack">
        <div className="toolbar">
            <div className="stack">
              <div className="status">{status}</div>
              <strong>{caseData.title}</strong>
              <div className="muted">
                {caseData.plaintiff} {"->"} {caseData.defendant}
              </div>
            </div>
          <span className="pill">{caseData.amount}</span>
        </div>

        <div className="card-muted">
          <div className="label">Описание</div>
          <div>{caseData.description || "Описание пока не заполнено."}</div>
        </div>

        <div className="grid two">
          <div className="card-muted">
            <div className="label">Ответственный юрист</div>
            <div>{caseData.responsibleLawyer || "не назначен"}</div>
          </div>
          <div className="card-muted">
            <div className="label">Документы</div>
            <div>{documents.length}</div>
          </div>
        </div>

        <div className="toolbar">
          <Link className="btn-secondary" href={`/cases/${caseData.id}/documents`}>
            Документы
          </Link>
          <Link className="btn-secondary" href={`/cases/${caseData.id}/facts`}>
            Факты
          </Link>
          <Link className="btn-secondary" href={`/cases/${caseData.id}/pretension`}>
            Претензия
          </Link>
          <Link className="btn-secondary" href={`/cases/${caseData.id}/claim`}>
            Иск
          </Link>
          <Link className="btn-secondary" href={`/cases/${caseData.id}/lawyer-review`}>
            Рабочее место юриста
          </Link>
        </div>

        {error ? <div className="status error">{error}</div> : null}
      </section>

      <section className="card stack">
        <div className="card-muted">
          <div className="label">Загрузка документов</div>
          {canRole(user, ["initiator", "lawyer", "admin"]) ? (
            <div className="stack">
              <input
                className="input"
                type="file"
                onChange={(event) => void uploadDocument(event.target.files?.[0] ?? null)}
                disabled={busy === "upload"}
              />
              <div className="subtle">Поддерживаются PDF, DOCX, XLSX, TXT, PNG, JPG. Имя файла нормализуется backend.</div>
            </div>
          ) : (
            <div className="status warning">Загрузка документов недоступна для вашей роли.</div>
          )}
        </div>

        <div className="card-muted">
          <div className="label">Извлеченные факты</div>
          <div className="toolbar">
            <button className="btn-secondary" type="button" disabled={!canRole(user, ["initiator", "lawyer", "admin"]) || busy === "extract"} onClick={() => void runExtraction()}>
              {busy === "extract" ? "Извлекаем..." : "Запустить извлечение"}
            </button>
            <span className="pill">{facts.length} фактов</span>
          </div>
          {facts.length === 0 ? <div className="muted-box">Факты ещё не извлечены.</div> : null}
          <div className="list">
            {facts.slice(0, 3).map((fact) => (
              <div className="list-item" key={fact.id}>
                <div>
                  <strong>{fact.title}</strong>
                  <div className="muted">{fact.value}</div>
                </div>
                <span className="pill">{Math.round(fact.confidence * 100)}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card-muted">
          <div className="label">Состояние черновиков</div>
          <div className="list">
            <div className="list-item">
              <div>
                <strong>Претензия</strong>
                <div className="muted">{pretension?.updatedAt ?? "не сгенерирована"}</div>
              </div>
              <span className="pill">{pretension?.approved ? "approved" : "draft"}</span>
            </div>
            <div className="list-item">
              <div>
                <strong>Иск</strong>
                <div className="muted">{claim?.updatedAt ?? "не сгенерирован"}</div>
              </div>
              <span className="pill">{claim?.approved ? "approved" : "draft"}</span>
            </div>
            <div className="list-item">
              <div>
                <strong>Checklist</strong>
                <div className="muted">
                  {checklist?.items.filter((item) => item.isCompleted).length ?? 0} / {checklist?.items.length ?? 0}
                </div>
              </div>
              <span className="pill">{checklist?.status ?? "n/a"}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
