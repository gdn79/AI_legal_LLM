"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "./app-shell";
import { canRole, useAuth } from "./providers";
import { EmptyState, ErrorState, LoadingState } from "./states";
import { apiClient } from "../lib/api-client";
import type { IntegrationApproval, IntegrationCredentialsStatus, IntegrationRequestLog, ProviderConnectionCheck, SandboxReadiness, SettingItem, SystemStatus } from "../lib/types";

type IntegrationName = "fns" | "russian_post" | "court_arbitr";

export function IntegrationSettingsPage({
  title,
  description,
  integrationName,
  filter,
}: {
  title: string;
  description: string;
  integrationName: IntegrationName;
  filter: (item: SettingItem) => boolean;
}) {
  const { user } = useAuth();
  const [items, setItems] = useState<SettingItem[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [sandboxReadiness, setSandboxReadiness] = useState<SandboxReadiness | null>(null);
  const [credentialsStatus, setCredentialsStatus] = useState<IntegrationCredentialsStatus | null>(null);
  const [activeApproval, setActiveApproval] = useState<IntegrationApproval | null>(null);
  const [lastTest, setLastTest] = useState<ProviderConnectionCheck | null>(null);
  const [lastError, setLastError] = useState<IntegrationRequestLog | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const allowed = canRole(user, ["admin"]);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void Promise.all([
      apiClient.listSettings(),
      apiClient.getSystemStatus(),
      apiClient.getSandboxReadiness(),
      apiClient.getIntegrationCredentialsStatus(),
      apiClient.listActiveIntegrationApprovals(),
      apiClient.listIntegrationLogs(integrationName, "test_connection"),
      apiClient.listIntegrationLogs(integrationName, undefined, "FAILED"),
    ])
      .then(([settings, systemStatus, readiness, credentials, activeApprovals, testLogs, errorLogs]) => {
        if (!active) return;
        setItems(settings);
        setStatus(systemStatus);
        setSandboxReadiness(readiness);
        setCredentialsStatus(credentials);
        setActiveApproval(activeApprovals.find((item) => mapApprovalIntegrationName(item.integrationName) === integrationName) ?? null);
        setLastTest(testLogs[0] ? mapLogToCheck(testLogs[0]) : null);
        setLastError(errorLogs[0] ?? null);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load integration settings.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed, integrationName]);

  const filtered = useMemo(() => items.filter(filter), [filter, items]);

  const integrationSummary = useMemo(() => {
    if (!status) return null;
    if (integrationName === "fns") {
      return {
        provider: status.fnsProvider,
        mode: status.fnsMode,
        sandboxEnabled: status.fnsSandboxEnabled,
        realEnabled: status.realFnsEnabled,
        warning: "Real FNS API is disabled. Only mock/manual/local flows are allowed in the current environment.",
      };
    }
    if (integrationName === "russian_post") {
      return {
        provider: status.russianPostProvider,
        mode: status.russianPostMode,
        sandboxEnabled: status.russianPostSandboxEnabled,
        realEnabled: status.realPostSendEnabled,
        warning: "Real Russian Post send is disabled. Only mock/manual flows are allowed in the current environment.",
      };
    }
    return {
      provider: status.courtArbitrProvider,
      mode: status.courtArbitrMode,
      sandboxEnabled: status.courtSandboxEnabled,
      realEnabled: status.realCourtSearchEnabled || status.publicKadSearchEnabled || status.courtSubmissionEnabled,
      warning: "Real court APIs and public KAD search are disabled. Only mock/manual flows are allowed in the current environment.",
    };
  }, [integrationName, status]);

  const readinessItem = useMemo(() => {
    if (!sandboxReadiness) return null;
    if (integrationName === "fns") return sandboxReadiness.fns;
    if (integrationName === "russian_post") return sandboxReadiness.russianPost;
    return sandboxReadiness.court;
  }, [integrationName, sandboxReadiness]);

  const credentialsItem = useMemo(() => {
    if (!credentialsStatus) return null;
    if (integrationName === "fns") return credentialsStatus.fns;
    if (integrationName === "russian_post") return credentialsStatus.russianPost;
    return credentialsStatus.courtArbitr;
  }, [credentialsStatus, integrationName]);

  const handleTestConnection = async () => {
    setTesting(true);
    setError(null);
    try {
      const result =
        integrationName === "fns"
          ? await apiClient.testFnsConnection(true)
          : integrationName === "russian_post"
            ? await apiClient.testRussianPostConnection(true)
            : await apiClient.testCourtArbitrConnection(true);
      setLastTest(result);
      const latestErrors = await apiClient.listIntegrationLogs(integrationName, undefined, "FAILED");
      setLastError(latestErrors[0] ?? null);
      setSandboxReadiness(await apiClient.getSandboxReadiness());
      setCredentialsStatus(await apiClient.getIntegrationCredentialsStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test connection failed");
    } finally {
      setTesting(false);
    }
  };

  return (
    <AppShell title={title} description={description}>
      {!allowed ? (
        <div data-testid="integration-settings-forbidden">
          <EmptyState title="Section unavailable" description="Integration settings are available to admin only." />
        </div>
      ) : null}
      {allowed && loading ? <LoadingState label="Loading integration settings..." /> : null}
      {allowed && error ? <ErrorState title="Integration settings error" message={error} /> : null}
      {allowed && !loading && !error ? (
        <div className="grid two" data-testid="integration-settings-loaded">
          <section className="card stack">
            <h2 className="section-title">Integration status</h2>
            <div className="card-muted">
              <div className="label">Mode</div>
              <div>{integrationSummary?.mode ?? "unknown"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Provider</div>
              <div>{integrationSummary?.provider ?? "unknown"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Sandbox flag</div>
              <div>{integrationSummary?.sandboxEnabled ? "enabled" : "disabled"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Sandbox credentials</div>
              <div>{credentialsItem?.sandboxCredentialsPresent ? "present" : "missing"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Real API</div>
              <div>{integrationSummary?.realEnabled ? "enabled" : "disabled"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Production credentials</div>
              <div>{credentialsItem?.productionCredentialsPresent ? "present" : "missing"}</div>
            </div>
            <div className="muted-box">{integrationSummary?.warning}</div>
            <button className="btn" type="button" onClick={handleTestConnection} disabled={testing}>
              {testing ? "Checking..." : "Test sandbox readiness"}
            </button>
          </section>

          <section className="card stack">
            <h2 className="section-title">Sandbox readiness</h2>
            <div className="card-muted">
              <div className="label">Approval</div>
              <div>{readinessItem?.approvalStatus ?? "unknown"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Active approval</div>
              <div>{readinessItem?.activeApproval ? "yes" : "no"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Approval expires</div>
              <div>{readinessItem?.approvalExpiresAt ?? activeApproval?.expiresAt ?? "not set"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Credentials</div>
              <div>{readinessItem?.credentialsPresent ? "present" : "missing"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Last test connection</div>
              <div>{lastTest ? `${lastTest.status}: ${lastTest.detail}` : readinessItem?.testConnectionStatus ?? "not_tested"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Last integration error</div>
              <div>{lastError ? `${lastError.errorCode || lastError.status}: ${lastError.errorMessage || "see safe metadata"}` : "No recent errors"}</div>
            </div>
            <div className="card-muted">
              <div className="label">Blocking reasons</div>
              <div>{readinessItem?.blockingReasons.length ? readinessItem.blockingReasons.join(", ") : "None"}</div>
            </div>
            <Link href="/settings/integrations/approvals">Open sandbox approvals</Link>
          </section>

          <section className="card stack" style={{ gridColumn: "1 / -1" }}>
            <h2 className="section-title">Backend settings</h2>
            {filtered.length === 0 ? (
              <EmptyState title="No settings found" description="No backend settings matched this integration filter." />
            ) : (
              <div className="list">
                {filtered.map((item) => (
                  <article key={item.key} className="list-item">
                    <div className="stack">
                      <strong>{item.key}</strong>
                      <div className="muted">{item.description || "No description"}</div>
                    </div>
                    <code>{item.value}</code>
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

function mapLogToCheck(log: IntegrationRequestLog): ProviderConnectionCheck {
  return {
    provider: log.provider,
    mode: log.mode,
    status: log.status,
    ok: log.status === "SUCCESS",
    detail: log.errorMessage || "Safe test connection completed.",
    externalCalls: false,
  };
}

function mapApprovalIntegrationName(name: IntegrationApproval["integrationName"]): IntegrationName {
  if (name === "FNS") return "fns";
  if (name === "RUSSIAN_POST") return "russian_post";
  return "court_arbitr";
}
