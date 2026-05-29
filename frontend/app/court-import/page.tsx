"use client";

import React, { FormEvent, useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { CourtImportJob, Organization } from "../../lib/types";

export default function CourtImportPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["lawyer", "manager", "admin"]);
  const canCreate = canRole(user, ["lawyer", "admin"]);
  const [jobs, setJobs] = useState<CourtImportJob[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [inn, setInn] = useState("");
  const [dateFrom, setDateFrom] = useState("2026-05-01");
  const [dateTo, setDateTo] = useState("2026-05-31");
  const [participationRole, setParticipationRole] = useState("claimant");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    Promise.all([apiClient.listCourtImportJobs(), apiClient.listOrganizations()])
      .then(([jobList, orgs]) => {
        if (!active) return;
        setJobs(jobList);
        setOrganizations(orgs);
        if (!organizationId && orgs[0]) {
          setOrganizationId(orgs[0].id);
          setInn(orgs[0].inn);
        }
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить court import");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, organizationId]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const job = await apiClient.createCourtImportJob({ organizationId, inn, dateFrom, dateTo, participationRole });
      setJobs((current) => [job, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать import job");
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppShell title="Загрузка дел" description="Mock/manual импорт дел за период из судебного источника.">
      {!allowed ? <EmptyState title="Раздел недоступен" description="Судебный импорт доступен lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем import jobs..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error ? (
        <div className="grid two">
          <section className="card stack">
            <h2 className="section-title">Новый import job</h2>
            {!canCreate ? <div className="status warning">Создание job доступно только lawyer и admin.</div> : null}
            <form className="stack" data-testid="court-import-form" onSubmit={submit}>
              <select className="select" value={organizationId} onChange={(event) => {
                const value = event.target.value;
                setOrganizationId(value);
                const organization = organizations.find((item) => item.id === value);
                setInn(organization?.inn ?? "");
              }} disabled={!canCreate}>
                {organizations.map((item) => (
                  <option key={item.id} value={item.id}>{item.shortName || item.inn}</option>
                ))}
              </select>
              <input className="input" value={inn} onChange={(event) => setInn(event.target.value)} disabled={!canCreate} />
              <input className="input" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} disabled={!canCreate} />
              <input className="input" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} disabled={!canCreate} />
              <select className="select" value={participationRole} onChange={(event) => setParticipationRole(event.target.value)} disabled={!canCreate}>
                <option value="claimant">claimant</option>
                <option value="respondent">respondent</option>
                <option value="any">any</option>
              </select>
              <button className="btn" type="submit" disabled={!canCreate || creating}>{creating ? "Создание..." : "Создать import job"}</button>
            </form>
          </section>
          <section className="card stack">
            <h2 className="section-title">История загрузок</h2>
            {jobs.length === 0 ? <div className="muted-box">Import jobs пока не найдены.</div> : null}
            {jobs.map((job) => (
              <article key={job.id} className="list-item">
                <div className="stack">
                  <a href={`/court-import/${job.id}`}>Job #{job.id}</a>
                  <div className="muted">{job.inn} · {job.dateFrom} → {job.dateTo}</div>
                </div>
                <span className="pill">{job.resultCount}</span>
              </article>
            ))}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
