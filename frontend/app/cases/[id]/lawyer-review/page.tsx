"use client";

import { useEffect, useMemo, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { canRole, useAuth } from "../../../../components/providers";
import { apiClient } from "../../../../lib/api-client";
import type { CaseDetailModel, Checklist, SignatoryAuthorityCheck } from "../../../../lib/types";

function LawyerReviewPanel({ data }: { data: CaseDetailModel }) {
  const { user } = useAuth();
  const [checklist, setChecklist] = useState<Checklist | null>(data.checklist ?? null);
  const [authorityChecks, setAuthorityChecks] = useState<SignatoryAuthorityCheck[]>([]);
  const [hasClaimCopyProof, setHasClaimCopyProof] = useState<boolean>(data.status === "COURT_PACKAGE_READY");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"pretension" | "claim" | "export" | null>(null);
  const canReview = canRole(user, ["lawyer"]);
  const canExport = canRole(user, ["lawyer", "admin"]);
  const citations = data.citations ?? [];

  useEffect(() => {
    setChecklist(data.checklist ?? null);
    setAuthorityChecks([]);
    setMessage(null);
    setError(null);
    setHasClaimCopyProof(data.status === "COURT_PACKAGE_READY");
  }, [data.id, data.checklist, data.status]);

  useEffect(() => {
    let active = true;
    void apiClient
      .getClaimCopyProof(data.id)
      .then((result) => {
        if (active) {
          setHasClaimCopyProof(result.hasClaimCopyProof);
        }
      })
      .catch(() => {
        if (active) {
          setHasClaimCopyProof(false);
        }
      });
    return () => {
      active = false;
    };
  }, [data.id]);

  useEffect(() => {
    let active = true;
    void apiClient
      .listAuthorityChecksByCase(data.id)
      .then((result) => {
        if (active) {
          setAuthorityChecks(result);
        }
      })
      .catch(() => {
        if (active) {
          setAuthorityChecks([]);
        }
      });
    return () => {
      active = false;
    };
  }, [data.id]);

  const incompleteCount = useMemo(() => checklist?.items.filter((item) => !item.isCompleted).length ?? 0, [checklist]);
  const canExportPackage =
    canExport && ["APPROVED_BY_LAWYER", "COURT_PACKAGE_READY"].includes(data.status) && hasClaimCopyProof;

  const toggleChecklistItem = async (itemId: string, nextValue: boolean, notes: string) => {
    try {
      const updated = await apiClient.updateChecklistItem(itemId, nextValue, notes);
      setChecklist((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) => (item.id === itemId ? updated : item)),
            }
          : current,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить чек-лист");
    }
  };

  const approvePretension = async () => {
    setBusy("pretension");
    setMessage(null);
    setError(null);
    try {
      await apiClient.approvePretension(data.id);
      setMessage("Претензия утверждена юристом.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось утвердить претензию");
    } finally {
      setBusy(null);
    }
  };

  const approveClaim = async () => {
    setBusy("claim");
    setMessage(null);
    setError(null);
    try {
      await apiClient.approveClaim(data.id);
      setMessage("Иск утвержден юристом.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось утвердить иск");
    } finally {
      setBusy(null);
    }
  };

  const exportPackage = async () => {
    setBusy("export");
    setMessage(null);
    setError(null);
    try {
      const result = await apiClient.exportCase(data.id);
      setMessage(`Комплект сформирован: ${result.filePath}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сформировать комплект");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid two">
      <section className="card stack">
        <div className="label">Проверка полномочий</div>
        {authorityChecks.length === 0 ? (
          <div className="status warning">Authority check not found. Требуется проверка юриста.</div>
        ) : (
          <div className="list" data-testid="authority-check-list">
            {authorityChecks.map((item) => (
              <article className="list-item" key={item.id}>
                <div className="stack">
                  <strong>{item.documentKind}</strong>
                  <div className="muted">{item.reason}</div>
                </div>
                <span className="pill">{item.result}</span>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="card stack">
        <div className="label">Риски</div>
        <div className="muted-box">
          {citations.length === 0
            ? "По делу не найдено подтвержденных правовых источников. Требуется проверка юриста."
            : `Найдено citations: ${citations.length}. Проверьте корректность привязки к иску и претензии.`}
        </div>
        <div className="muted-box">
          Автоматическое юридическое утверждение запрещено. Текущий статус дела: {data.status}.
        </div>
        <div className="muted-box">
          Черновики:
          <br />
          претензия {data.pretension?.approved ? "утверждена" : "не утверждена"},
          <br />
          иск {data.claim?.approved ? "утвержден" : "не утвержден"}.
        </div>
        <div className={hasClaimCopyProof ? "status" : "status warning"} data-testid="claim-copy-proof-state">
          {hasClaimCopyProof
            ? "Доказательство направления копии иска ответчику подтверждено."
            : "Нет подтвержденного доказательства направления копии иска ответчику."}
        </div>
      </section>

      <section className="card stack">
        <div className="toolbar">
          <div>
            <div className="label">Чек-лист</div>
            <div className="muted">Незакрытых пунктов: {incompleteCount}</div>
          </div>
          {checklist ? <span className="pill">{checklist.status}</span> : null}
        </div>
        {checklist?.items.length ? (
          <div className="list">
            {checklist.items.map((item) => (
              <article className="list-item" key={item.id}>
                <div className="stack" style={{ flex: 1 }}>
                  <strong>{item.title}</strong>
                  <input
                    className="input"
                    value={item.notes}
                    onChange={(event) =>
                      setChecklist((current) =>
                        current
                          ? {
                              ...current,
                              items: current.items.map((currentItem) =>
                                currentItem.id === item.id ? { ...currentItem, notes: event.target.value } : currentItem,
                              ),
                            }
                          : current,
                      )
                    }
                    disabled={!canReview}
                    placeholder="Комментарий юриста"
                  />
                </div>
                <button
                  className={item.isCompleted ? "btn-secondary" : "btn"}
                  type="button"
                  disabled={!canReview}
                  onClick={() => toggleChecklistItem(item.id, !item.isCompleted, item.notes)}
                >
                  {item.isCompleted ? "Снять" : "Закрыть"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className="muted-box">Чек-лист пока не сформирован.</div>
        )}
      </section>

      <section className="card stack">
        <div className="label">Источники RAG</div>
        {citations.length === 0 ? (
          <div className="status warning">Источник не найден, требуется проверка юриста.</div>
        ) : (
          <div className="list">
            {citations.map((citation) => (
              <article className="list-item" key={citation.id}>
                <div className="stack">
                  <strong>{citation.targetType}</strong>
                  <div className="muted">{citation.quote}</div>
                </div>
                <span className="pill">source {citation.sourceId}</span>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="card stack">
        <div className="label">Действия юриста</div>
        {!canReview ? <div className="status warning">Утверждение претензии и иска доступно только lawyer.</div> : null}
        {!canExport ? <div className="status warning">Экспорт комплекта скрыт для вашей роли.</div> : null}
        {message ? <div className="status">{message}</div> : null}
        {error ? <div className="status error">{error}</div> : null}
        <div className="toolbar">
          <button className="btn-secondary" type="button" onClick={approvePretension} disabled={!canReview || busy !== null}>
            {busy === "pretension" ? "Утверждение..." : "Утвердить претензию"}
          </button>
          <button className="btn" type="button" onClick={approveClaim} disabled={!canReview || busy !== null}>
            {busy === "claim" ? "Утверждение..." : "Утвердить иск"}
          </button>
          <button
            className="btn-secondary"
            data-testid="export-package-button"
            type="button"
            onClick={exportPackage}
            disabled={!canExportPackage || busy !== null}
          >
            {busy === "export" ? "Экспорт..." : "Экспортировать комплект"}
          </button>
        </div>
        {!canExportPackage ? (
          <div className="muted">
            Экспорт доступен только после утверждения иска, подтверждения proof-of-service и только ролям lawyer/admin.
          </div>
        ) : null}
      </section>
    </div>
  );
}

export default function LawyerReviewPage() {
  return (
    <CaseSubpage
      title="Проверка юриста"
      description="Рабочее место юриста: риски, чек-лист, источники и контроль утверждения."
      render={(data) => <LawyerReviewPanel data={data} />}
    />
  );
}
