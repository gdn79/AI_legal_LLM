"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { canRole, useAuth } from "../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { FnsLookupLog, Organization, OrganizationSnapshot } from "../../../lib/types";

export default function OrganizationDetailPage() {
  const params = useParams<{ id: string }>();
  const organizationId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const { user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [snapshots, setSnapshots] = useState<OrganizationSnapshot[]>([]);
  const [lookupLogs, setLookupLogs] = useState<FnsLookupLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const allowed = canRole(user, ["lawyer", "manager", "admin"]);

  useEffect(() => {
    if (!allowed || !organizationId) {
      setLoading(false);
      return;
    }
    let active = true;
    Promise.all([
      apiClient.getOrganization(organizationId),
      apiClient.listOrganizationSnapshots(organizationId),
      apiClient.listFnsLookupLogs(organizationId),
    ])
      .then(([item, snapshotList, logList]) => {
        if (!active) return;
        setOrganization(item);
        setSnapshots(snapshotList);
        setLookupLogs(logList);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить организацию");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, organizationId]);

  return (
    <AppShell
      title={organization ? organization.shortName || organization.inn : "Организация"}
      description="Карточка организации, snapshots ФНС и история lookup."
      actions={
        organizationId ? (
          <div className="pill-row">
            <Link className="chip" href={`/organizations/${organizationId}/employees`}>Сотрудники</Link>
            <Link className="chip" href={`/organizations/${organizationId}/signatories`}>Подписанты</Link>
            <Link className="chip" href={`/organizations/${organizationId}/powers-of-attorney`}>Доверенности</Link>
          </div>
        ) : undefined
      }
    >
      {!allowed ? <EmptyState title="Раздел недоступен" description="Карточка организации доступна lawyer, manager и admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем организацию..." /> : null}
      {allowed && error ? <ErrorState title="Ошибка загрузки" message={error} /> : null}
      {allowed && !loading && !error && !organization ? <EmptyState title="Организация не найдена" description="Backend не вернул карточку организации." /> : null}
      {allowed && !loading && !error && organization ? (
        <div className="grid two">
          <section className="card stack">
            <h2 className="section-title">Основные данные</h2>
            <div className="muted-box">ИНН: {organization.inn}</div>
            <div className="muted-box">КПП: {organization.kpp || "—"}</div>
            <div className="muted-box">ОГРН: {organization.ogrn || "—"}</div>
            <div className="muted-box">Адрес: {organization.legalAddress || "—"}</div>
            <div className="muted-box">Руководитель: {organization.currentDirectorName || "—"}</div>
            <div className="muted-box">Статус проверки: {organization.reviewStatus}</div>
          </section>
          <section className="card stack">
            <h2 className="section-title">Lookup ФНС</h2>
            {lookupLogs.length === 0 ? <div className="muted-box">История lookup пока пуста.</div> : null}
            {lookupLogs.map((log) => (
              <article key={log.id} className="list-item">
                <div className="stack">
                  <strong>{log.providerMode}</strong>
                  <div className="muted">{log.reviewStatus}</div>
                </div>
                <code>{log.createdAt}</code>
              </article>
            ))}
          </section>
          <section className="card stack" style={{ gridColumn: "1 / -1" }}>
            <h2 className="section-title">Snapshots</h2>
            {snapshots.length === 0 ? <div className="muted-box">Snapshots не найдены.</div> : null}
            {snapshots.map((snapshot) => (
              <article key={snapshot.id} className="list-item">
                <div className="stack">
                  <strong>{snapshot.source}</strong>
                  <div className="muted">{snapshot.actualAt}</div>
                </div>
                <code>{snapshot.rawPayload.slice(0, 120)}...</code>
              </article>
            ))}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
