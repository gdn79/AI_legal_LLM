"use client";

import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { AuditEntry } from "../../lib/types";

export default function AuditPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const allowed = canRole(user, ["admin"]);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    apiClient
      .listAudit()
      .then((result) => {
        if (active) {
          setItems(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить аудит");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Журнал аудита" description="Панель просмотра критичных действий и системных событий.">
      {!allowed ? <EmptyState title="Доступ к аудиту закрыт" description="Эта страница доступна только роли admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем аудит..." /> : null}
      {allowed && error ? <ErrorState title="Не удалось загрузить аудит" message={error} /> : null}
      {allowed && !loading && !error ? (
        <section className="card" data-testid="audit-loaded">
          {items.length === 0 ? (
            <div className="muted-box">Событий пока нет.</div>
          ) : (
            <div className="list">
              {items.map((item) => (
                <div className="list-item" key={item.id}>
                  <div className="stack">
                    <strong>{item.action}</strong>
                    <div className="muted">
                      {item.entityType} #{item.entityId}
                    </div>
                    <div className="muted">{item.details || "без деталей"}</div>
                    <div className="muted">{item.createdAt}</div>
                  </div>
                  <span className="pill">{item.requestId}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </AppShell>
  );
}
