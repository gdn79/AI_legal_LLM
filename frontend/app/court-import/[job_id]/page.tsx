"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { EmptyState, ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { CourtImportJob, ExternalCourtCase } from "../../../lib/types";

export default function CourtImportJobPage() {
  const params = useParams<{ job_id: string }>();
  const jobId = Array.isArray(params?.job_id) ? params.job_id[0] : params?.job_id;
  const [job, setJob] = useState<CourtImportJob | null>(null);
  const [cases, setCases] = useState<ExternalCourtCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setLoading(false);
      return;
    }
    let active = true;
    Promise.all([apiClient.getCourtImportJob(jobId), apiClient.listCourtImportCases(jobId)])
      .then(([jobItem, caseItems]) => {
        if (!active) return;
        setJob(jobItem);
        setCases(caseItems);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить import job");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [jobId]);

  return (
    <AppShell title={job ? `Import job #${job.id}` : "Import job"} description="Просмотр найденных дел по периоду.">
      {loading ? <LoadingState label="Загружаем import job..." /> : null}
      {error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {!loading && !error && !job ? <EmptyState title="Job не найден" description="Backend не вернул import job." /> : null}
      {!loading && !error && job ? (
        <div className="grid two">
          <section className="card stack">
            <div className="muted-box">ИНН: {job.inn}</div>
            <div className="muted-box">Период: {job.dateFrom} → {job.dateTo}</div>
            <div className="muted-box">Статус: {job.status}</div>
          </section>
          <section className="card stack">
            <h2 className="section-title">Найденные дела</h2>
            {cases.length === 0 ? <div className="muted-box">Внешние дела не найдены.</div> : null}
            {cases.map((item) => (
              <article key={item.id} className="list-item">
                <div className="stack">
                  <a href={`/external-court-cases/${item.id}`}>{item.caseNumber}</a>
                  <div className="muted">{item.courtName || "суд не указан"}</div>
                </div>
                <span className="pill">{item.participantRole}</span>
              </article>
            ))}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
