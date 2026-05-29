"use client";

import React, { useEffect, useMemo, useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { canRole, useAuth } from "../../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";
import type { SettingItem } from "../../../lib/types";

export default function LlmRagSettingsPage() {
  const { user } = useAuth();
  const allowed = canRole(user, ["admin"]);
  const [items, setItems] = useState<SettingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    void apiClient
      .listSettings()
      .then((result) => {
        if (!active) return;
        setItems(result);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load LLM/RAG settings");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const key = item.key.toUpperCase();
      return key.includes("LLM") || key.includes("RAG") || key.includes("QDRANT");
    });
  }, [items]);

  return (
    <AppShell
      title="LLM / RAG Settings"
      description="Backend settings for local LLM, embeddings, and RAG components."
    >
      {!allowed ? (
        <EmptyState title="Section unavailable" description="Only admin can view integration settings." />
      ) : null}
      {allowed && loading ? <LoadingState label="Loading LLM / RAG settings..." /> : null}
      {allowed && error ? <ErrorState title="Failed to load settings" message={error} /> : null}
      {allowed && !loading && !error ? (
        filtered.length === 0 ? (
          <EmptyState title="No settings found" description="No backend LLM/RAG settings are available yet." />
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
        )
      ) : null}
    </AppShell>
  );
}
