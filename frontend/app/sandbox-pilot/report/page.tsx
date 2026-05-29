"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { canRole, useAuth } from "../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { SandboxPilotReport } from "../../../lib/types";

export default function SandboxPilotReportPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["admin", "manager"]);
  const [report, setReport] = useState<SandboxPilotReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .getSandboxPilotReport()
      .then((result) => {
        if (active) setReport(result);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load sandbox pilot report.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Sandbox pilot report" description="Read-only report for the limited sandbox pilot run.">
      {!allowed ? <EmptyState title="Access denied" description="Sandbox pilot report is available for manager and admin." /> : null}
      {allowed && loading ? <LoadingState label="Loading sandbox pilot report..." /> : null}
      {allowed && error ? <ErrorState title="Sandbox pilot report error" message={error} /> : null}
      {allowed && !loading && !error && report ? (
        <div className="grid two" data-testid="sandbox-pilot-report-page">
          <section className="card stack">
            <div className="label">Summary</div>
            <div className="list">
              <article className="list-item"><span>Status</span><strong>{report.status}</strong></article>
              <article className="list-item"><span>Recommendation</span><strong>{report.recommendation}</strong></article>
              <article className="list-item"><span>Credentials</span><strong>{report.realSandboxCredentials}</strong></article>
              <article className="list-item"><span>Live calls</span><strong>{report.liveSandboxCalls}</strong></article>
            </div>
          </section>
          <section className="card stack">
            <div className="label">Safety gates</div>
            <div className="list">
              <article className="list-item"><span>Production API</span><strong>{report.productionApi}</strong></article>
              <article className="list-item"><span>Court submission</span><strong>{report.courtSubmission}</strong></article>
              <article className="list-item"><span>Secrets leakage</span><strong>{report.secretsLeakage}</strong></article>
              <article className="list-item"><span>Export generated</span><strong>{String(report.exportGenerated)}</strong></article>
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
