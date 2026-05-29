"use client";

import { useState } from "react";
import type { CaseCreateInput } from "../lib/types";

const emptyValues: CaseCreateInput = {
  title: "",
  plaintiff: "",
  defendant: "",
  amount: "",
  responsibleLawyerId: "",
  description: "",
};

export function CaseForm({
  onSubmit,
  submitting,
  error,
}: {
  onSubmit: (values: CaseCreateInput) => Promise<void>;
  submitting: boolean;
  error: string | null;
}) {
  const [values, setValues] = useState<CaseCreateInput>(emptyValues);

  const updateField = <K extends keyof CaseCreateInput>(field: K, value: CaseCreateInput[K]) => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  return (
    <section className="card">
      <form
        className="grid two"
        onSubmit={async (event) => {
          event.preventDefault();
          await onSubmit(values);
        }}
      >
        <div>
          <label className="label" htmlFor="title">
            Название дела
          </label>
          <input id="title" className="input" value={values.title} onChange={(event) => updateField("title", event.target.value)} required />
        </div>

        <div>
          <label className="label" htmlFor="plaintiff">
            Истец
          </label>
          <input id="plaintiff" className="input" value={values.plaintiff} onChange={(event) => updateField("plaintiff", event.target.value)} required />
        </div>

        <div>
          <label className="label" htmlFor="defendant">
            Ответчик
          </label>
          <input id="defendant" className="input" value={values.defendant} onChange={(event) => updateField("defendant", event.target.value)} required />
        </div>

        <div>
          <label className="label" htmlFor="amount">
            Сумма требований
          </label>
          <input id="amount" className="input" value={values.amount} onChange={(event) => updateField("amount", event.target.value)} required />
        </div>

        <div>
          <label className="label" htmlFor="responsibleLawyer">
            Ответственный юрист ID
          </label>
          <input
            id="responsibleLawyer"
            className="input"
            value={values.responsibleLawyerId ?? ""}
            onChange={(event) => updateField("responsibleLawyerId", event.target.value)}
            placeholder="2"
          />
        </div>

        <div style={{ gridColumn: "1 / -1" }}>
          <label className="label" htmlFor="description">
            Описание
          </label>
          <textarea id="description" className="textarea" value={values.description} onChange={(event) => updateField("description", event.target.value)} />
        </div>

        {error ? (
          <div className="status error" style={{ gridColumn: "1 / -1" }}>
            {error}
          </div>
        ) : null}

        <div className="toolbar" style={{ gridColumn: "1 / -1" }}>
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? "Сохраняем..." : "Создать дело"}
          </button>
        </div>
      </form>
    </section>
  );
}
