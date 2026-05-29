"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { AppShell } from "./app-shell";
import { EmptyState, ErrorState, LoadingState } from "./states";
import { apiClient } from "../lib/api-client";
import type { CaseDetailModel } from "../lib/types";

const tabs = [
  ["", "Card"],
  ["/documents", "Documents"],
  ["/facts", "Facts"],
  ["/pretension", "Pretension"],
  ["/claim", "Claim"],
  ["/lawyer-review", "Lawyer review"],
  ["/timeline", "Timeline"],
  ["/feedback", "Feedback"],
  ["/postal-dispatches", "Postal"],
  ["/court", "Court"],
  ["/court-submission", "Court package"],
] as const;

export function CaseSubpage({
  title,
  description,
  render,
}: {
  title: string;
  description: string;
  render: (data: CaseDetailModel) => ReactNode;
}) {
  const params = useParams<{ id: string }>();
  const caseId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [data, setData] = useState<CaseDetailModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) {
      setError("Case id is missing.");
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .getCase(caseId)
      .then((result) => {
        if (!active) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load case.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  return (
    <AppShell
      title={`${title}${caseId ? ` · Case ${caseId}` : ""}`}
      description={description}
      actions={
        caseId ? (
          <div className="pill-row">
            {tabs.map(([suffix, label]) => (
              <Link key={suffix || "root"} className="chip" href={`/cases/${caseId}${suffix}`}>
                {label}
              </Link>
            ))}
          </div>
        ) : undefined
      }
    >
      {loading ? <LoadingState label="Loading case..." /> : null}
      {error ? <ErrorState title="Case load error" message={error} /> : null}
      {!loading && !error && !data ? <EmptyState title="No data" description="This case has no loaded data yet." /> : null}
      {!loading && !error && data ? render(data) : null}
    </AppShell>
  );
}
