"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { CaseList } from "../../components/case-list";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { CaseSummary } from "../../lib/types";

export default function CasesPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canCreate = canRole(user, ["initiator", "admin"]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiClient
      .listCases()
      .then((data) => {
        if (!active) {
          return;
        }
        setCases(data);
        setError(null);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "Не удалось загрузить дела");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <AppShell
      title="Дела"
      description="Список юридических дел с фильтрацией по ролям и backend-контрактом."
      actions={
        canCreate ? (
          <Link className="btn" href="/cases/new">
            Создать дело
          </Link>
        ) : null
      }
    >
      {loading ? <LoadingState label="Загружаем дела..." /> : null}
      {error ? <ErrorState title="Не удалось получить список дел" message={error} /> : null}
      {!loading && !error && cases.length === 0 ? (
        <EmptyState
          title="Дел пока нет"
          description={canCreate ? "Создайте первое дело, чтобы загрузить документы и начать работу." : "Доступных дел пока нет."}
          action={canCreate ? <Link className="btn" href="/cases/new">Создать дело</Link> : undefined}
        />
      ) : null}
      {!loading && !error && cases.length > 0 ? <CaseList cases={cases} /> : null}
    </AppShell>
  );
}
