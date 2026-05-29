"use client";

import { useEffect, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { canRole, useAuth } from "../../../../components/providers";
import { EmptyState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { CaseDetailModel, CaseFact } from "../../../../lib/types";

function FactsPanel({ data }: { data: CaseDetailModel }) {
  const { user } = useAuth();
  const [facts, setFacts] = useState<CaseFact[]>(data.facts);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canExtract = canRole(user, ["initiator", "lawyer", "admin"]);

  useEffect(() => {
    setFacts(data.facts);
    setWarnings([]);
    setError(null);
  }, [data.id, data.facts]);

  const runExtraction = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.runExtraction(data.id);
      setFacts(result.facts);
      setWarnings(result.warnings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось запустить извлечение фактов");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stack">
      <section className="card stack">
        <div className="toolbar">
          <div>
            <h2 className="section-title">Извлеченные факты</h2>
            <p className="subtle">Факты формируются через backend extraction и доступны для дальнейшей генерации претензии и иска.</p>
          </div>
          {canExtract ? (
            <button className="btn" type="button" onClick={runExtraction} disabled={loading}>
              {loading ? "Извлечение..." : "Запустить извлечение"}
            </button>
          ) : null}
        </div>
        {error ? <div className="status error">{error}</div> : null}
        {!canExtract ? <div className="status warning">Запуск извлечения доступен только initiator, lawyer и admin.</div> : null}
        {warnings.length > 0 ? (
          <div className="stack">
            {warnings.map((warning) => (
              <div className="status warning" key={warning}>
                {warning}
              </div>
            ))}
          </div>
        ) : null}
      </section>

      {facts.length === 0 ? (
        <EmptyState title="Факты пока не извлечены" description="Запустите extraction, чтобы заполнить карточку фактов и подготовить материалы для юриста." />
      ) : (
        <section className="card">
          <div className="list">
            {facts.map((fact) => (
              <article className="list-item" key={fact.id}>
                <div className="stack">
                  <strong>{fact.title}</strong>
                  <div className="muted">{fact.value}</div>
                  {fact.source ? <div className="muted">Источник: {fact.source}</div> : null}
                </div>
                {fact.confidence ? <span className="pill">confidence {fact.confidence}</span> : null}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default function CaseFactsPage() {
  return (
    <CaseSubpage
      title="Факты"
      description="Извлеченные факты по делу и их источники."
      render={(data) => <FactsPanel data={data} />}
    />
  );
}
