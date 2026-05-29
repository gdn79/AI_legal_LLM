"use client";

import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { DashboardModel } from "../../lib/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const allowed = canRole(user, ["manager", "admin"]);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    apiClient
      .getDashboard()
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить дашборд");
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
    <AppShell title="Дашборд" description="Панель руководителя и администратора с основными метриками дел.">
      {!allowed ? <EmptyState title="Дашборд недоступен" description="Эта страница доступна только ролям manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем метрики..." /> : null}
      {allowed && error ? <ErrorState title="Не удалось загрузить дашборд" message={error} /> : null}
      {allowed && !loading && !error && data ? (
        <div className="grid three" data-testid="dashboard-loaded">
          <section className="card">
            <div className="muted">Роль пользователя</div>
            <h2 className="section-title">{data.userRole}</h2>
            <p className="subtle">Доступ к управленческим метрикам и чтению дел определяется backend RBAC.</p>
          </section>
          <section className="card">
            <div className="muted">Всего дел</div>
            <h2 className="section-title">{data.totalCases}</h2>
            <p className="subtle">Счетчик приходит из backend `/api/dashboard` или из mock/manual режима.</p>
          </section>
          <section className="card">
            <div className="muted">Текущая роль</div>
            <h2 className="section-title">{user?.role ?? "guest"}</h2>
            <p className="subtle">UI скрывает недоступные действия и оставляет только чтение там, где редактирование запрещено.</p>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
