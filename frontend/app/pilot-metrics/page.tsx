"use client";

import React from "react";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { PilotMetricsSummary, PilotReport } from "../../lib/types";

export default function PilotMetricsPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["manager", "admin"]);
  const [summary, setSummary] = useState<PilotMetricsSummary | null>(null);
  const [report, setReport] = useState<PilotReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .getPilotMetricsSummary()
      .then((result) => {
        if (!active) return;
        setSummary(result);
      })
      .then(() => apiClient.getPilotReport("2026-05-01", "2026-05-31"))
      .then((result) => {
        if (!active) return;
        setReport(result);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load pilot metrics.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  return (
    <AppShell title="Pilot metrics" description="Summary metrics for the internal mock/manual pilot." >
      {!allowed ? <EmptyState title="Access denied" description="Pilot metrics are available for manager and admin." /> : null}
      {allowed && loading ? <LoadingState label="Loading pilot metrics..." /> : null}
      {allowed && error ? <ErrorState title="Pilot metrics error" message={error} /> : null}
      {allowed && !loading && !error && summary ? (
        <div className="grid two" data-testid="pilot-metrics-page">
          <section className="card stack">
            <div className="label">Summary</div>
            <div className="list">
              <article className="list-item"><span>Total cases</span><strong>{summary.totalCases}</strong></article>
              <article className="list-item"><span>Happy path cases</span><strong>{summary.completedHappyPathCases}</strong></article>
              <article className="list-item"><span>Blocked cases</span><strong>{summary.blockedCases}</strong></article>
              <article className="list-item"><span>Feedback items</span><strong>{summary.totalFeedbackItems}</strong></article>
              <article className="list-item"><span>RAG warnings</span><strong>{summary.totalRagWarnings}</strong></article>
              <article className="list-item"><span>Authority warnings</span><strong>{summary.totalAuthorityWarnings}</strong></article>
              <article className="list-item"><span>Authority invalids</span><strong>{summary.totalAuthorityInvalids}</strong></article>
              <article className="list-item"><span>Authority checks</span><strong>{summary.totalAuthorityChecks}</strong></article>
            </div>
          </section>
          <section className="card stack">
            <div className="label">Per case</div>
            <div className="list">
              {summary.cases.map((item) => (
                <article key={item.caseId} className="list-item">
                  <div className="stack">
                    <strong>{item.title}</strong>
                    <div className="muted">Status: {item.status}</div>
                    <div className="muted">Authority invalids: {item.authorityInvalids}</div>
                  </div>
                  <span className="pill">{item.blockedActions} blocked</span>
                </article>
              ))}
            </div>
          </section>
          <section className="card stack">
            <div className="label">Authority breakdown</div>
            <div className="list">
              {summary.authorityByCase.map((item) => (
                <article key={item.caseId} className="list-item">
                  <div className="stack">
                    <strong>{item.title}</strong>
                    <div className="muted">valid: {item.validCount}</div>
                    <div className="muted" data-testid={`authority-invalid-${item.caseId}`}>invalid: {item.invalidCount}</div>
                  </div>
                  <span className="pill">{item.blockedActionsCount} blocked</span>
                </article>
              ))}
            </div>
          </section>
          <section className="card stack">
            <div className="label">Pilot report</div>
            {report ? (
              <div className="list">
                <article className="list-item"><span>Recommendation</span><strong data-testid="pilot-report-recommendation">{report.recommendation}</strong></article>
                <article className="list-item"><span>Unresolved items</span><strong data-testid="pilot-report-unresolved">{report.unresolvedItems.length}</strong></article>
              </div>
            ) : (
              <div className="muted">Report is loading.</div>
            )}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
