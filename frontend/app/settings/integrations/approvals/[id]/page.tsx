"use client";

import React from "react";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "../../../../../components/app-shell";
import { canRole, useAuth } from "../../../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../../../components/states";
import { apiClient } from "../../../../../lib/api-client";
import type { IntegrationApproval } from "../../../../../lib/types";

export default function IntegrationApprovalDetailPage() {
  const params = useParams<{ id: string }>();
  const approvalId = String(params?.id ?? "");
  const { user } = useAuth();
  const allowed = canRole(user, ["admin"]);
  const [item, setItem] = useState<IntegrationApproval | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("Reviewed in sandbox control panel.");
  const [acting, setActing] = useState(false);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .getIntegrationApproval(approvalId)
      .then((result) => {
        if (!active) return;
        setItem(result);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load approval.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, approvalId]);

  const act = async (action: "approve" | "reject" | "revoke") => {
    setActing(true);
    setError(null);
    try {
      const next =
        action === "approve"
          ? await apiClient.approveIntegrationApproval(approvalId, reason)
          : action === "reject"
            ? await apiClient.rejectIntegrationApproval(approvalId, reason)
            : await apiClient.revokeIntegrationApproval(approvalId, reason);
      setItem(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update approval.");
    } finally {
      setActing(false);
    }
  };

  return (
    <AppShell
      title="Sandbox approval detail"
      description="Inspect approval status, expiry and admin actions. Production enablement remains disabled."
    >
      {!allowed ? <EmptyState title="Access denied" description="Sandbox approval details are available to admin only." /> : null}
      {allowed && loading ? <LoadingState label="Loading approval..." /> : null}
      {allowed && error ? <ErrorState title="Sandbox approval error" message={error} /> : null}
      {allowed && !loading && !error && item ? (
        <div className="grid two" data-testid="integration-approval-detail-page">
          <section className="card stack">
            <h2 className="section-title">Approval status</h2>
            <div className="card-muted">
              <div className="label">Integration</div>
              <div>{item.integrationName}</div>
            </div>
            <div className="card-muted">
              <div className="label">Environment</div>
              <div>{item.environment}</div>
            </div>
            <div className="card-muted">
              <div className="label">Status</div>
              <div>{item.status}</div>
            </div>
            <div className="card-muted">
              <div className="label">Expires at</div>
              <div>{item.expiresAt ?? "not set"}</div>
            </div>
            <div className="muted-box">{item.reason}</div>
          </section>

          <section className="card stack">
            <h2 className="section-title">Admin action</h2>
            <label className="stack">
              <span className="label">Reason</span>
              <input className="input" value={reason} onChange={(event) => setReason(event.target.value)} />
            </label>
            <div className="toolbar">
              <button className="btn" type="button" onClick={() => act("approve")} disabled={acting}>
                Approve sandbox
              </button>
              <button className="btn secondary" type="button" onClick={() => act("reject")} disabled={acting}>
                Reject
              </button>
              <button className="btn secondary" type="button" onClick={() => act("revoke")} disabled={acting}>
                Revoke
              </button>
            </div>
            <div className="muted-box">Production API approval stays blocked even if a production request exists.</div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}
