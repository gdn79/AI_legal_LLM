"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { EmptyState, ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { ExternalCourtCase } from "../../../lib/types";

export default function ExternalCourtCaseDetailPage() {
  const params = useParams<{ id: string }>();
  const externalCaseId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [item, setItem] = useState<ExternalCourtCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!externalCaseId) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .getExternalCourtCase(externalCaseId)
      .then((result) => {
        if (!active) return;
        setItem(result);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить внешнее дело");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [externalCaseId]);

  return (
    <AppShell title={item ? item.caseNumber : "Внешнее дело"} description="События и snapshots импортированного судебного дела.">
      {loading ? <LoadingState label="Загружаем внешнее дело..." /> : null}
      {error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {!loading && !error && !item ? <EmptyState title="Дело не найдено" description="Backend не вернул данные по внешнему делу." /> : null}
      {!loading && !error && item ? (
        <div className="grid two">
          <section className="card stack">
            <div className="muted-box">Суд: {item.courtName || "—"}</div>
            <div className="muted-box">Роль: {item.participantRole}</div>
            <div className="muted-box" data-testid="linked-internal-case">Linked internal case: {item.linkedCaseId || "none"}</div>
            <div className="muted-box">Hash: {item.payloadHash}</div>
          </section>
          <section className="card stack">
            <h2 className="section-title">События</h2>
            {item.events.length === 0 ? <div className="muted-box">События отсутствуют.</div> : null}
            {item.events.map((event) => (
              <article key={event.id} className="list-item">
                <div className="stack">
                  <strong>{event.eventType}</strong>
                  <div className="muted">{event.description}</div>
                </div>
                <span className="pill">{event.eventDate || "—"}</span>
              </article>
            ))}
          </section>
          <section className="card stack" style={{ gridColumn: "1 / -1" }}>
            <h2 className="section-title">Snapshots</h2>
            {item.snapshots.length === 0 ? <div className="muted-box">Snapshots отсутствуют.</div> : null}
            {item.snapshots.map((snapshot) => (
              <article key={snapshot.id} className="list-item">
                <div className="stack">
                  <strong>{snapshot.source}</strong>
                  <div className="muted">{snapshot.snapshotHash}</div>
                </div>
                <code>{snapshot.snapshotPayload.slice(0, 120)}...</code>
              </article>
            ))}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
