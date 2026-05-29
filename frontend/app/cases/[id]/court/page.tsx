"use client";

import React from "react";
import { useEffect, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { EmptyState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { ExternalCourtCase } from "../../../../lib/types";

export default function CaseCourtPage() {
  return (
    <CaseSubpage
      title="Судебный контур"
      description="Привязанные внешние судебные дела, события и snapshots."
      render={(data) => <CourtPanel caseId={data.id} />}
    />
  );
}

function CourtPanel({ caseId }: { caseId: string }) {
  const [items, setItems] = useState<ExternalCourtCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void apiClient
      .listExternalCourtCases()
      .then((result) => {
        if (!active) return;
        setItems(result.filter((item) => item.linkedCaseId === caseId));
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить судебные данные");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  if (loading) return <section className="card">Загружаем судебные дела...</section>;
  if (error) return <section className="card"><div className="status error">{error}</div></section>;
  if (items.length === 0) return <EmptyState title="Внешние дела не найдены" description="К делу пока не привязаны внешние судебные дела." />;
  return (
    <section className="card stack">
      {items.map((item) => (
        <article key={item.id} className="list-item">
          <div className="stack">
            <strong>{item.caseNumber}</strong>
            <div className="muted">{item.courtName || "суд не указан"}</div>
            <div className="muted">Событий: {item.events.length} · Snapshots: {item.snapshots.length}</div>
          </div>
          <span className="pill">{item.participantRole}</span>
        </article>
      ))}
    </section>
  );
}
