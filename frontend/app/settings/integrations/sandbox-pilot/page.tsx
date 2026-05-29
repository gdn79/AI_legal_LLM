"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "../../../../components/app-shell";
import { canRole, useAuth } from "../../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { SandboxPilotMetrics, SandboxPilotReport } from "../../../../lib/types";

export default function SandboxPilotSettingsPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["admin", "manager"]);
  const [metrics, setMetrics] = useState<SandboxPilotMetrics | null>(null);
  const [report, setReport] = useState<SandboxPilotReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void Promise.all([apiClient.getSandboxPilotMetrics(), apiClient.getSandboxPilotReport()])
      .then(([nextMetrics, nextReport]) => {
        if (!active) return;
        setMetrics(nextMetrics);
        setReport(nextReport);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load sandbox pilot status.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Sandbox pilot" description="Limited sandbox pilot readiness and safety status.">
      {!allowed ? <EmptyState title="Access denied" description="Sandbox pilot status is available for manager and admin." /> : null}
      {allowed && loading ? <LoadingState label="Loading sandbox pilot status..." /> : null}
      {allowed && error ? <ErrorState title="Sandbox pilot error" message={error} /> : null}
      {allowed && !loading && !error && metrics && report ? (
        <div className="grid two" data-testid="sandbox-pilot-settings-page">
          <section className="card stack">
            <div className="label">Summary</div>
            <div className="list">
              <article className="list-item"><span>Status</span><strong>{report.status}</strong></article>
              <article className="list-item"><span>Credentials</span><strong>{report.realSandboxCredentials}</strong></article>
              <article className="list-item"><span>Live sandbox calls</span><strong>{report.liveSandboxCalls}</strong></article>
              <article className="list-item"><span>Production API</span><strong>{report.productionApi}</strong></article>
            </div>
            <div className="muted-box">Production API stays disabled. Dangerous operations remain blocked or dry-run only.</div>
          </section>

          <section className="card stack">
            <div className="label">Metrics</div>
            <div className="list">
              <article className="list-item"><span>Skipped checks</span><strong>{metrics.sandboxTestConnectionsSkipped}</strong></article>
              <article className="list-item"><span>Failed checks</span><strong>{metrics.sandboxTestConnectionsFailed}</strong></article>
              <article className="list-item"><span>Dry runs</span><strong>{metrics.sandboxDryRunsTotal}</strong></article>
              <article className="list-item"><span>Blocked dangerous ops</span><strong>{metrics.sandboxDangerousOperationsBlocked}</strong></article>
            </div>
          </section>

          <section className="card stack">
            <div className="label">Approvals</div>
            <div className="list">
              <article className="list-item"><span>FNS approval</span><strong>{report.fns.approvalStatus}</strong></article>
              <article className="list-item"><span>Russian Post approval</span><strong>{report.russianPost.approvalStatus}</strong></article>
              <article className="list-item"><span>Court approval</span><strong>{report.courtArbitr.approvalStatus}</strong></article>
            </div>
            <Link href="/settings/integrations/approvals">Open approvals</Link>
          </section>

          <section className="card stack">
            <div className="label">Links</div>
            <Link href="/sandbox-pilot/metrics">Open sandbox pilot metrics</Link>
            <Link href="/sandbox-pilot/report">Open sandbox pilot report</Link>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
