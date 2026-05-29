"use client";

import React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { ExternalCourtCase } from "../../lib/types";

export default function ExternalCourtCasesPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<ExternalCourtCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const allowed = canRole(user, ["lawyer", "manager", "admin"]);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .listExternalCourtCases()
      .then((result) => {
        if (!active) return;
        setItems(result);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить внешние дела");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Внешние судебные дела" description="Список дел, импортированных из mock/manual судебного источника.">
      {!allowed ? <EmptyState title="Раздел недоступен" description="Внешние судебные дела доступны lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем внешние дела..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error && items.length === 0 ? <EmptyState title="Внешние дела не найдены" description="Сначала выполните court import." /> : null}
      {allowed && !loading && !error && items.length > 0 ? (
        <section className="card stack">
          {items.map((item) => (
            <article key={item.id} className="list-item">
              <div className="stack">
                <Link href={`/external-court-cases/${item.id}`}>{item.caseNumber}</Link>
                <div className="muted">{item.courtName || "суд не указан"}</div>
              </div>
              <span className="pill">{item.payloadHash.slice(0, 8)}</span>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  );
}
