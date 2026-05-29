"use client";

import React, { useState } from "react";
import { CaseSubpage } from "../../../../components/case-subpage";
import { RoleGuard } from "../../../../components/providers";
import { apiClient } from "../../../../lib/api-client";

export default function CaseCourtSubmissionPage() {
  return (
    <CaseSubpage
      title="Комплект суда"
      description="Ручная подготовка судебного комплекта после прохождения COURT_PACKAGE_READY."
      render={(data) => <CourtSubmissionPanel caseId={data.id} />}
    />
  );
}

function CourtSubmissionPanel({ caseId }: { caseId: string }) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const prepare = async () => {
    setLoading(true);
    setError(null);
    try {
      const item = await apiClient.prepareCourtSubmission({ caseId, note: "Prepared from frontend MVP" });
      setMessage(`Комплект подготовлен: ${item.packagePath}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось подготовить комплект");
    } finally {
      setLoading(false);
    }
  };

  return (
    <RoleGuard allowed={["lawyer", "admin"]}>
      <section className="card stack">
        <div className="muted-box">Подготовка комплекта не подает документы автоматически. Она только формирует package для ручной подачи.</div>
        {message ? <div className="status">{message}</div> : null}
        {error ? <div className="status error">{error}</div> : null}
        <button className="btn" type="button" onClick={prepare} disabled={loading}>
          {loading ? "Подготовка..." : "Подготовить комплект суда"}
        </button>
      </section>
    </RoleGuard>
  );
}
