"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../../components/app-shell";
import { canRole, useAuth } from "../../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { Signatory, SignatoryAuthorityCheck } from "../../../../lib/types";

export default function OrganizationSignatoriesPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const { user } = useAuth();
  const [items, setItems] = useState<Array<Signatory & { checks: SignatoryAuthorityCheck[] }>>([]);
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
      .listSignatories(organizationId)
      .then(async (result) => {
        const withChecks = await Promise.all(result.map(async (item) => ({ ...item, checks: await apiClient.listSignatoryChecks(item.id) })));
        if (active) setItems(withChecks);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить подписантов");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, organizationId]);

  return (
    <AppShell title="Подписанты" description="Подписанты организации и история проверки полномочий.">
      {!allowed ? <EmptyState title="Раздел недоступен" description="Подписанты доступны lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем подписантов..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error && items.length === 0 ? <EmptyState title="Подписанты не найдены" description="Для организации пока не создано ни одного подписанта." /> : null}
      {allowed && !loading && !error && items.length > 0 ? (
        <section className="card stack">
          {items.map((item) => (
            <article key={item.id} className="list-item">
              <div className="stack">
                <strong>{item.fullName}</strong>
                <div className="muted">{item.signatoryType} · {item.authorityBasis}</div>
                <div className="muted">Проверок полномочий: {item.checks.length}</div>
              </div>
              <span className="pill">{item.isActive ? "active" : "inactive"}</span>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  );
}
