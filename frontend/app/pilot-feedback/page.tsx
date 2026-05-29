"use client";

import React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { PilotFeedback } from "../../lib/types";

export default function PilotFeedbackPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["lawyer", "manager", "admin"]);
  const [items, setItems] = useState<PilotFeedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [module, setModule] = useState("");

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .listPilotFeedback({ status: status || undefined, severity: severity || undefined, module: module || undefined })
      .then((result) => {
        if (!active) return;
        setItems(result);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load pilot feedback.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, module, severity, status]);

  return (
    <AppShell title="Pilot feedback" description="Cross-case list of pilot remarks, grouped for triage.">
      {!allowed ? <EmptyState title="Access denied" description="Pilot feedback list is available for lawyer, manager and admin." /> : null}
      {allowed && loading ? <LoadingState label="Loading feedback..." /> : null}
      {allowed && error ? <ErrorState title="Pilot feedback error" message={error} /> : null}
      {allowed && !loading && !error ? (
        <>
          <section className="card toolbar" data-testid="pilot-feedback-filters">
            <select className="input" value={module} onChange={(event) => setModule(event.target.value)}>
              <option value="">All modules</option>
              {["AUTHORITY", "DOCUMENTS", "FACT_EXTRACTION", "PRETENSION", "CLAIM", "RAG", "POSTAL", "COURT", "EXPORT", "AUDIT", "UI", "OTHER"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select className="input" value={severity} onChange={(event) => setSeverity(event.target.value)}>
              <option value="">All severities</option>
              {["BLOCKER", "HIGH", "MEDIUM", "LOW", "IDEA"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All statuses</option>
              {["NEW", "TRIAGED", "IN_PROGRESS", "FIXED", "WONT_FIX", "POSTPONED"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </section>
          {items.length === 0 ? (
            <EmptyState title="No feedback" description="No pilot remarks match the current filters." />
          ) : (
            <section className="card stack" data-testid="pilot-feedback-list">
              {items.map((item) => (
                <article key={item.id} className="list-item">
                  <div className="stack">
                    <strong>{item.title}</strong>
                    <div className="muted">{item.module} · {item.severity} · {item.status}</div>
                    <div className="muted">{item.description}</div>
                    {item.caseId ? <Link href={`/cases/${item.caseId}`}>Open case</Link> : null}
                  </div>
                  <span className="pill">{item.role}</span>
                </article>
              ))}
            </section>
          )}
        </>
      ) : null}
    </AppShell>
  );
}
