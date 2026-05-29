"use client";

import { useEffect, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { canRole, useAuth } from "../../../../components/providers";
import { apiClient } from "../../../../lib/api-client";
import type { CaseDetailModel, DraftDocument } from "../../../../lib/types";

function PretensionEditor({ data }: { data: CaseDetailModel }) {
  const { user } = useAuth();
  const [draft, setDraft] = useState<DraftDocument | null>(data.pretension ?? null);
  const [content, setContent] = useState(data.pretension?.content ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"generate" | "save" | "approve" | null>(null);
  const canEdit = canRole(user, ["lawyer"]);

  useEffect(() => {
    setDraft(data.pretension ?? null);
    setContent(data.pretension?.content ?? "");
    setMessage(null);
    setError(null);
  }, [data.id, data.pretension]);

  const generate = async () => {
    setBusy("generate");
    setError(null);
    setMessage(null);
    try {
      const next = await apiClient.generatePretension(data.id);
      setDraft(next);
      setContent(next.content);
      setMessage("Черновик претензии сгенерирован.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сгенерировать претензию");
    } finally {
      setBusy(null);
    }
  };

  const save = async () => {
    setBusy("save");
    setError(null);
    setMessage(null);
    try {
      const next = await apiClient.updatePretension(data.id, content);
      setDraft(next);
      setMessage("Черновик претензии сохранен.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить претензию");
    } finally {
      setBusy(null);
    }
  };

  const approve = async () => {
    setBusy("approve");
    setError(null);
    setMessage(null);
    try {
      await apiClient.approvePretension(data.id);
      const next = await apiClient.getPretension(data.id);
      setDraft(next);
      setContent(next.content);
      setMessage("Претензия утверждена юристом.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось утвердить претензию");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="card stack">
      <div className="toolbar">
        <div>
          <h2 className="section-title">Претензия</h2>
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
              {busy === "approve" ? "Утверждение..." : "Утвердить претензию"}
            </button>
          </div>
        ) : null}
      </div>

      {!canEdit ? <div className="status warning">Редактирование и утверждение претензии доступно только lawyer.</div> : null}
      {message ? <div className="status">{message}</div> : null}
      {error ? <div className="status error">{error}</div> : null}

      <div className="muted-box">
        AI готовит только черновик. Юридически значимое утверждение выполняет юрист через backend workflow.
      </div>

      <textarea className="textarea" value={content} onChange={(event) => setContent(event.target.value)} readOnly={!canEdit} />
    </section>
  );
}

export default function PretensionPage() {
  return (
    <CaseSubpage
      title="Претензия"
      description="Черновик претензии, подготовленный системой и проверяемый юристом."
      render={(data) => <PretensionEditor data={data} />}
    />
  );
}
