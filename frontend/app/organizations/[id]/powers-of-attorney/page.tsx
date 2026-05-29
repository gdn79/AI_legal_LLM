"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../../components/app-shell";
import { canRole, useAuth } from "../../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { Employee, PowerOfAttorney } from "../../../../lib/types";

export default function OrganizationPowersOfAttorneyPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const { user } = useAuth();
  const [items, setItems] = useState<Array<PowerOfAttorney & { employeeName?: string }>>([]);
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
      .then(async (employees) => {
        const employeeMap = new Map<string, Employee>(employees.map((employee) => [employee.id, employee]));
        const powers = (await Promise.all(employees.map((employee) => apiClient.listPowersForEmployee(employee.id)))).flat();
        if (active) setItems(powers.map((power) => ({ ...power, employeeName: employeeMap.get(power.employeeId)?.fullName })));
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить доверенности");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, organizationId]);

  return (
    <AppShell title="Доверенности" description="Доверенности сотрудников и статусы полномочий.">
      {!allowed ? <EmptyState title="Раздел недоступен" description="Доверенности доступны lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем доверенности..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error && items.length === 0 ? <EmptyState title="Доверенности не найдены" description="Для сотрудников организации пока нет доверенностей." /> : null}
      {allowed && !loading && !error && items.length > 0 ? (
        <section className="card stack">
          {items.map((item) => (
            <article key={item.id} className="list-item">
              <div className="stack">
                <strong>{item.number}</strong>
                <div className="muted">{item.employeeName || item.employeeId}</div>
                <div className="muted">{item.authorityScope.join(", ")}</div>
              </div>
              <span className="pill">{item.status}</span>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  );
}
