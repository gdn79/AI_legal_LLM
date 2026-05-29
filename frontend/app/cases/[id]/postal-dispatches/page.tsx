"use client";

import React from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { EmptyState } from "../../../../components/states";
import { useEffect, useState } from "react";
import { apiClient } from "../../../../lib/api-client";
import type { PostalDispatch } from "../../../../lib/types";

export default function CasePostalDispatchesPage() {
  return (
    <CaseSubpage
      title="Почтовые отправления"
      description="Отправка претензии и копии иска, proof-of-service и статусы."
      render={(data) => <PostalPanel caseId={data.id} />}
    />
  );
}

function PostalPanel({ caseId }: { caseId: string }) {
  const [items, setItems] = useState<PostalDispatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void apiClient
      .listPostalDispatches(caseId)
      .then((result) => {
        if (!active) return;
        setItems(result);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить отправления");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  if (loading) return <section className="card">Загружаем отправления...</section>;
  if (error) return <section className="card"><div className="status error">{error}</div></section>;
  if (items.length === 0) return <EmptyState title="Отправления не найдены" description="По делу пока не создано почтовых отправлений." />;
  return (
    <section className="card stack">
      {items.map((item) => (
        <article key={item.id} className="list-item">
          <div className="stack">
            <strong>{item.dispatchKind}</strong>
            <div className="muted">{item.recipientName} · {item.recipientAddress}</div>
          </div>
          <span className="pill">{item.status}</span>
        </article>
      ))}
    </section>
  );
}
