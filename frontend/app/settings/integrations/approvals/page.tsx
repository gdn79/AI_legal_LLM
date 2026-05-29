"use client";

import React from "react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../../../../components/app-shell";
import { canRole, useAuth } from "../../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { IntegrationApproval } from "../../../../lib/types";

export default function IntegrationApprovalsPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["admin"]);
  const [items, setItems] = useState<IntegrationApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [integrationName, setIntegrationName] = useState("");
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("Sandbox validation request");
  const [expiresAt, setExpiresAt] = useState("2026-06-30T12:00:00Z");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    void apiClient
      .listIntegrationApprovals({
        integrationName: integrationName || undefined,
        status: status || undefined,
      })
      .then((result) => {
        if (!active) return;
        setItems(result);
        setError(null);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load approvals.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, integrationName, status]);

  const activeApprovals = useMemo(
    () => items.filter((item) => item.environment === "SANDBOX" && item.status === "APPROVED"),
    [items],
  );

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      await apiClient.createIntegrationApproval({
        integrationName: "FNS",
        environment: "SANDBOX",
        reason,
        expiresAt,
      });
      setItems(await apiClient.listIntegrationApprovals());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create approval.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppShell
      title="Sandbox approvals"
      description="Approval workflow for sandbox-only integration enablement. Production approvals remain disabled."
    >
      {!allowed ? <EmptyState title="Access denied" description="Sandbox approvals are available to admin only." /> : null}
      {allowed && loading ? <LoadingState label="Loading sandbox approvals..." /> : null}
      {allowed && error ? <ErrorState title="Sandbox approvals error" message={error} /> : null}
      {allowed && !loading && !error ? (
        <div className="grid two" data-testid="integration-approvals-page">
          <section className="card stack">
            <h2 className="section-title">Request sandbox approval</h2>
            <div className="muted-box">Production API enablement is still forbidden in this environment.</div>
            <label className="stack">
              <span className="label">Reason</span>
              <input className="input" value={reason} onChange={(event) => setReason(event.target.value)} />
            </label>
            <label className="stack">
              <span className="label">Expires at</span>
              <input className="input" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} />
            </label>
            <button className="btn" type="button" onClick={handleCreate} disabled={creating}>
              {creating ? "Requesting..." : "Request FNS sandbox approval"}
            </button>
          </section>

          <section className="card stack">
            <h2 className="section-title">Filters</h2>
            <select className="input" value={integrationName} onChange={(event) => setIntegrationName(event.target.value)}>
              <option value="">All integrations</option>
              <option value="FNS">FNS</option>
              <option value="RUSSIAN_POST">RUSSIAN_POST</option>
              <option value="COURT_ARBITR">COURT_ARBITR</option>
            </select>
            <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All statuses</option>
              {["REQUESTED", "APPROVED", "REJECTED", "EXPIRED", "REVOKED"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <div className="card-muted">
              <div className="label">Active sandbox approvals</div>
              <div>{activeApprovals.length}</div>
            </div>
          </section>

          <section className="card stack" style={{ gridColumn: "1 / -1" }}>
            <h2 className="section-title">Approval list</h2>
            {items.length === 0 ? (
              <EmptyState title="No approvals" description="No integration approvals match the current filters." />
            ) : (
              <div className="list">
                {items.map((item) => (
                  <article key={item.id} className="list-item">
                    <div className="stack">
                      <strong>{item.integrationName}</strong>
                      <div className="muted">
                        {item.environment} · {item.status}
                      </div>
                      <div className="muted">Expires: {item.expiresAt ?? "not set"}</div>
                    </div>
                    <Link href={`/settings/integrations/approvals/${item.id}`}>Open</Link>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
