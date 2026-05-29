"use client";

import React from "react";
import { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { SystemStatus } from "../../../lib/types";

export default function SystemStatusPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void apiClient
      .getSystemStatus()
      .then((result) => {
        if (!active) return;
        setStatus(result);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Не удалось загрузить system status");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <AppShell title="System status" description="Operational status и integration modes без секретов.">
      {loading ? <LoadingState label="Загружаем system status..." /> : null}
      {!loading && error ? <ErrorState title="Ошибка загрузки status" message={error} /> : null}
      {!loading && !error && status ? (
        <div className="grid two" data-testid="system-status-loaded">
          {[
            ["backend", status.backend],
            ["database", status.database],
            ["storage", status.storage],
            ["redis", status.redis],
            ["worker", status.worker],
            ["vector_db", status.vectorDb],
            ["llm", status.llm],
            ["fns_mode", status.fnsMode],
            ["russian_post_mode", status.russianPostMode],
            ["court_arbitr_mode", status.courtArbitrMode],
            ["fns_sandbox_enabled", String(status.fnsSandboxEnabled)],
            ["russian_post_sandbox_enabled", String(status.russianPostSandboxEnabled)],
            ["court_sandbox_enabled", String(status.courtSandboxEnabled)],
          ].map(([label, value]) => (
            <section className="card stack" key={label}>
              <div className="label">{label}</div>
              <strong>{value}</strong>
            </section>
          ))}
          <section className="card stack" style={{ gridColumn: "1 / -1" }}>
            <div className="label">Real API flags</div>
            <div className="list">
              <div className="list-item"><strong>ENABLE_REAL_FNS</strong><code>{String(status.realFnsEnabled)}</code></div>
              <div className="list-item"><strong>ENABLE_REAL_POST_SEND</strong><code>{String(status.realPostSendEnabled)}</code></div>
              <div className="list-item"><strong>ENABLE_REAL_COURT_SEARCH</strong><code>{String(status.realCourtSearchEnabled)}</code></div>
              <div className="list-item"><strong>ENABLE_PUBLIC_KAD_SEARCH</strong><code>{String(status.publicKadSearchEnabled)}</code></div>
              <div className="list-item"><strong>ENABLE_COURT_SUBMISSION</strong><code>{String(status.courtSubmissionEnabled)}</code></div>
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
