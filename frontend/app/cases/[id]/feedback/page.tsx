"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { canRole, useAuth } from "../../../../components/providers";
import { apiClient } from "../../../../lib/api-client";
import type { CaseDetailModel, PilotFeedback } from "../../../../lib/types";

const defaultForm = {
  module: "UI",
  severity: "LOW",
  title: "",
  description: "",
  expectedBehavior: "",
  actualBehavior: "",
};

function FeedbackPanel({ data }: { data: CaseDetailModel }) {
  const { user } = useAuth();
  const params = useParams<{ id: string }>();
  const caseId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [items, setItems] = useState<PilotFeedback[]>([]);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const canCreate = canRole(user, ["initiator", "lawyer", "admin", "manager"]);
  const canTriage = canRole(user, ["lawyer", "admin", "manager"]);

  useEffect(() => {
    if (!caseId) return;
    let active = true;
    void apiClient
      .listPilotFeedback({ caseId })
      .then((result) => {
        if (!active) return;
        setItems(result);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load feedback.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  const submit = async () => {
    if (!caseId) return;
    setError(null);
    setMessage(null);
    try {
      const created = await apiClient.createPilotFeedback({
        caseId,
        module: form.module,
        severity: form.severity,
        title: form.title,
        description: form.description,
        expectedBehavior: form.expectedBehavior,
        actualBehavior: form.actualBehavior,
      });
      setItems((current) => [created, ...current]);
      setForm(defaultForm);
      setMessage("Feedback saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save feedback.");
    }
  };

  const updateStatus = async (feedbackId: string, status: string) => {
    setError(null);
    try {
      const updated = await apiClient.updatePilotFeedback(feedbackId, { status });
      setItems((current) => current.map((item) => (item.id === feedbackId ? updated : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update feedback status.");
    }
  };

  return (
    <div className="grid two" data-testid="case-feedback-page">
      <section className="card stack">
        <div className="label">Case feedback</div>
        <div className="muted-box">Case: {data.title}</div>
        {message ? <div className="status">{message}</div> : null}
        {error ? <div className="status error">{error}</div> : null}
        {canCreate ? (
          <>
            <input className="input" placeholder="Title" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} data-testid="feedback-title" />
            <select className="input" value={form.module} onChange={(event) => setForm((current) => ({ ...current, module: event.target.value }))}>
              {["ORGANIZATION", "AUTHORITY", "DOCUMENTS", "FACT_EXTRACTION", "PRETENSION", "CLAIM", "RAG", "POSTAL", "COURT", "EXPORT", "AUDIT", "DASHBOARD", "UI", "OTHER"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select className="input" value={form.severity} onChange={(event) => setForm((current) => ({ ...current, severity: event.target.value }))}>
              {["BLOCKER", "HIGH", "MEDIUM", "LOW", "IDEA"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <textarea className="input" placeholder="Description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
            <textarea className="input" placeholder="Expected behavior" value={form.expectedBehavior} onChange={(event) => setForm((current) => ({ ...current, expectedBehavior: event.target.value }))} />
            <textarea className="input" placeholder="Actual behavior" value={form.actualBehavior} onChange={(event) => setForm((current) => ({ ...current, actualBehavior: event.target.value }))} />
            <button className="btn" type="button" onClick={submit} data-testid="feedback-submit">
              Save feedback
            </button>
          </>
        ) : (
          <div className="status warning">Feedback creation is hidden for your role.</div>
        )}
      </section>

      <section className="card stack">
        <div className="label">Feedback items</div>
        {loading ? <div className="status">Loading...</div> : null}
        {!loading && items.length === 0 ? <div className="muted-box">No feedback items for this case yet.</div> : null}
        {!loading && items.length > 0 ? (
          <div className="list" data-testid="case-feedback-list">
            {items.map((item) => (
              <article className="list-item" key={item.id}>
                <div className="stack">
                  <strong>{item.title}</strong>
                  <div className="muted">{item.module} · {item.severity} · {item.status}</div>
                  <div className="muted">{item.description}</div>
                  {item.caseId ? <Link href={`/cases/${item.caseId}`}>Open case</Link> : null}
                </div>
                {canTriage ? (
                  <select className="input" value={item.status} onChange={(event) => updateStatus(item.id, event.target.value)}>
                    {["NEW", "TRIAGED", "IN_PROGRESS", "FIXED", "WONT_FIX", "POSTPONED"].map((status) => (
                      <option key={status} value={status}>
                        {status}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="pill">{item.status}</span>
                )}
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}

export default function CaseFeedbackPage() {
  return (
    <CaseSubpage
      title="Pilot feedback"
      description="Collect lawyer and pilot remarks for the current case."
      render={(data) => <FeedbackPanel data={data} />}
    />
  );
}
