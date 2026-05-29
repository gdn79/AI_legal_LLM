"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { EmptyState, ErrorState, LoadingState } from "../../../../components/states";
import { apiClient } from "../../../../lib/api-client";
import type { PilotTimelineEvent } from "../../../../lib/types";

export default function CaseTimelinePage() {
  const params = useParams<{ id: string }>();
  const caseId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [timeline, setTimeline] = useState<PilotTimelineEvent[] | null>(null);
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
      .getPilotCaseTimeline(caseId)
      .then((result) => {
        if (!active) return;
        setTimeline(result);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load case timeline.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  return (
    <CaseSubpage
      title="Case timeline"
      description="Chronological pilot timeline assembled from workflow, audit, proofs, court events, feedback, and exports."
      render={() => (
        <section className="card stack" data-testid="case-timeline-page">
          {loading ? <LoadingState label="Loading timeline..." /> : null}
          {error ? <ErrorState title="Timeline error" message={error} /> : null}
          {!loading && !error && (!timeline || timeline.length === 0) ? (
            <EmptyState title="No timeline data" description="No timeline events were collected for this case." />
          ) : null}
          {!loading && !error && timeline?.length ? (
            <div className="list" data-testid="timeline-event-list">
              {timeline.map((event) => (
                <article key={event.id} className="list-item">
                  <div className="stack">
                    <strong>{event.title}</strong>
                    <div className="muted">{event.eventType}</div>
                    <div>{event.description}</div>
                  </div>
                  <span className="pill">{new Date(event.createdAt).toLocaleString()}</span>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      )}
    />
  );
}
