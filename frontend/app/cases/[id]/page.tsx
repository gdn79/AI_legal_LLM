"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { CaseDetail } from "../../../components/case-detail";
import { ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { CaseDetailModel } from "../../../lib/types";

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const caseId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [data, setData] = useState<CaseDetailModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) {
      setError("Не указан идентификатор дела");
      setLoading(false);
      return;
    }

    let active = true;
    apiClient
      .getCase(caseId)
      .then((result) => {
        if (!active) return;
        setData(result);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить дело");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [caseId]);

  return (
    <AppShell title={`Дело ${caseId}`} description="Карточка дела, документы и действия workflow.">
      {loading ? <LoadingState label="Открываем карточку дела..." /> : null}
      {error ? <ErrorState title="Ошибка загрузки дела" message={error} /> : null}
      {!loading && !error && data ? <CaseDetail caseData={data} /> : null}
    </AppShell>
  );
}
