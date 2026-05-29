"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../../components/app-shell";
import { canRole, useAuth } from "../../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { Employee } from "../../../../lib/types";

export default function OrganizationEmployeesPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const { user } = useAuth();
  const [items, setItems] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const allowed = canRole(user, ["lawyer", "manager", "admin"]);

  useEffect(() => {
    if (!allowed || !organizationId) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .listEmployees(organizationId)
      .then((result) => {
        if (!active) return;
        setItems(result);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить сотрудников");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, organizationId]);

  return (
    <AppShell title="Сотрудники" description="История и текущий состав сотрудников организации.">
      {!allowed ? <EmptyState title="Раздел недоступен" description="Список сотрудников доступен lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем сотрудников..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error && items.length === 0 ? <EmptyState title="Сотрудники не найдены" description="В этой организации пока нет сотрудников." /> : null}
      {allowed && !loading && !error && items.length > 0 ? (
        <section className="card stack">
          {items.map((item) => (
            <article key={item.id} className="list-item">
              <div className="stack">
                <strong>{item.fullName}</strong>
                <div className="muted">{item.position || "должность не указана"}</div>
              </div>
              <span className="pill">{item.email || "без email"}</span>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  );
}
