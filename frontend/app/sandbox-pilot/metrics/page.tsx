"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { canRole, useAuth } from "../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { SandboxPilotMetrics } from "../../../lib/types";

export default function SandboxPilotMetricsPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["admin", "manager"]);
  const [metrics, setMetrics] = useState<SandboxPilotMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .getSandboxPilotMetrics()
      .then((result) => {
        if (active) setMetrics(result);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load sandbox metrics.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Sandbox pilot metrics" description="Operational metrics for the limited sandbox pilot.">
      {!allowed ? <EmptyState title="Access denied" description="Sandbox pilot metrics are available for manager and admin." /> : null}
      {allowed && loading ? <LoadingState label="Loading sandbox pilot metrics..." /> : null}
      {allowed && error ? <ErrorState title="Sandbox pilot metrics error" message={error} /> : null}
      {allowed && !loading && !error && metrics ? (
        <div className="grid two" data-testid="sandbox-pilot-metrics-page">
          <section className="card stack">
            <div className="label">Counters</div>
            <div className="list">
              <article className="list-item"><span>Test connections</span><strong>{metrics.sandboxTestConnectionsTotal}</strong></article>
              <article className="list-item"><span>Skipped</span><strong>{metrics.sandboxTestConnectionsSkipped}</strong></article>
              <article className="list-item"><span>Failed</span><strong>{metrics.sandboxTestConnectionsFailed}</strong></article>
              <article className="list-item"><span>Dry runs</span><strong>{metrics.sandboxDryRunsTotal}</strong></article>
              <article className="list-item"><span>Blocked ops</span><strong>{metrics.sandboxDangerousOperationsBlocked}</strong></article>
            </div>
          </section>
          <section className="card stack">
            <div className="label">Safety</div>
            <div className="list">
              <article className="list-item"><span>Credentials missing</span><strong>{metrics.credentialsMissingCount}</strong></article>
              <article className="list-item"><span>Approval required</span><strong>{metrics.approvalRequiredCount}</strong></article>
              <article className="list-item"><span>Approval expired</span><strong>{metrics.approvalExpiredCount}</strong></article>
              <article className="list-item"><span>Secret leakage findings</span><strong>{metrics.secretsLeakageFindings}</strong></article>
              <article className="list-item"><span>Production flags enabled</span><strong>{metrics.productionFlagsEnabledCount}</strong></article>
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
