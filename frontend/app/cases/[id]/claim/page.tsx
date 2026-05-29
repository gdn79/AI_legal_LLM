"use client";

import { useEffect, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { canRole, useAuth } from "../../../../components/providers";
import { apiClient } from "../../../../lib/api-client";
import type { CaseDetailModel, DraftDocument } from "../../../../lib/types";

function ClaimEditor({ data }: { data: CaseDetailModel }) {
  const { user } = useAuth();
  const [draft, setDraft] = useState<DraftDocument | null>(data.claim ?? null);
  const [content, setContent] = useState(data.claim?.content ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"generate" | "save" | "approve" | null>(null);
  const canEdit = canRole(user, ["lawyer"]);
  const citations = data.citations ?? [];

  useEffect(() => {
    setDraft(data.claim ?? null);
    setContent(data.claim?.content ?? "");
    setMessage(null);
    setError(null);
  }, [data.id, data.claim]);

  const generate = async () => {
    setBusy("generate");
    setError(null);
    setMessage(null);
    try {
      const next = await apiClient.generateClaim(data.id);
      setDraft(next);
      setContent(next.content);
      setMessage("Черновик иска сгенерирован.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сгенерировать иск");
    } finally {
      setBusy(null);
    }
  };

  const save = async () => {
    setBusy("save");
    setError(null);
    setMessage(null);
    try {
      const next = await apiClient.updateClaim(data.id, content);
      setDraft(next);
      setMessage("Черновик иска сохранен.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить иск");
    } finally {
      setBusy(null);
    }
  };

  const approve = async () => {
    setBusy("approve");
    setError(null);
    setMessage(null);
    try {
      await apiClient.approveClaim(data.id);
      const next = await apiClient.getClaim(data.id);
      setDraft(next);
      setContent(next.content);
      setMessage("Иск утвержден юристом.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось утвердить иск");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid two">
      <section className="card stack">
        <div className="toolbar">
          <div>
            <h2 className="section-title">Иск</h2>
            <div className="pill-row">
              <span className="pill">{data.status}</span>
              <span className="pill">{draft?.approved ? "approved" : "draft"}</span>
            </div>
          </div>
          {canEdit ? (
            <div className="pill-row">
              <button className="btn-secondary" type="button" onClick={generate} disabled={busy !== null}>
                {busy === "generate" ? "Генерация..." : "Сгенерировать"}
              </button>
              <button className="btn-secondary" type="button" onClick={save} disabled={busy !== null}>
                {busy === "save" ? "Сохранение..." : "Сохранить"}
              </button>
              <button className="btn" type="button" onClick={approve} disabled={busy !== null || !content.trim()}>
                {busy === "approve" ? "Утверждение..." : "Утвердить иск"}
              </button>
            </div>
          ) : null}
        </div>

        {!canEdit ? <div className="status warning">Редактирование и утверждение иска доступно только lawyer.</div> : null}
        {message ? <div className="status">{message}</div> : null}
        {error ? <div className="status error">{error}</div> : null}

        <div className="muted-box">
          Если источник права не найден, решение принимает юрист. AI не утверждает иск автоматически.
        </div>

        <textarea className="textarea" value={content} onChange={(event) => setContent(event.target.value)} readOnly={!canEdit} />
      </section>

      <section className="card stack">
        <h2 className="section-title">RAG-источники</h2>
        {citations.length === 0 ? (
          <div className="status warning">Источник не найден, требуется проверка юриста.</div>
        ) : (
          <div className="list">
            {citations.map((citation) => (
              <article className="list-item" key={citation.id}>
                <div className="stack">
                  <strong>{citation.quote.slice(0, 80)}</strong>
                  <div className="muted">source_id: {citation.sourceId}</div>
                </div>
                <span className="pill">{citation.targetType}</span>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function ClaimPage() {
  return (
    <CaseSubpage
      title="Иск"
      description="Черновик искового заявления с обязательной проверкой юриста."
      render={(data) => <ClaimEditor data={data} />}
    />
  );
}
