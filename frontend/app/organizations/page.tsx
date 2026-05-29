"use client";

import React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { Organization } from "../../lib/types";

export default function OrganizationsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Organization[]>([]);
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
      .listOrganizations()
      .then((result) => {
        if (!active) return;
        setItems(result);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить организации");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Организации" description="Справочник организаций-истцов и данные ФНС.">
      {!allowed ? <EmptyState title="Раздел недоступен" description="Справочник организаций доступен lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем организации..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error && items.length === 0 ? (
        <EmptyState title="Организации не найдены" description="Добавьте организацию через backend API или seed-данные." />
      ) : null}
      {allowed && !loading && !error && items.length > 0 ? (
        <section className="card stack">
          {items.map((item) => (
            <article key={item.id} className="list-item">
              <div className="stack">
                <Link href={`/organizations/${item.id}`}>{item.shortName || item.fullName || item.inn}</Link>
                <div className="muted">ИНН {item.inn} · КПП {item.kpp || "—"} · {item.reviewStatus}</div>
              </div>
              <span className="pill">{item.currentDirectorName || "директор не указан"}</span>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  );
}
