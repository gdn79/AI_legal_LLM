"use client";

import { type FormEvent, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { apiClient } from "../../lib/api-client";
import type { RagSource } from "../../lib/types";

export default function LegalSourcesPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RagSource[]>([]);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [fragment, setFragment] = useState("");
  const [sourceType, setSourceType] = useState("law");
  const canCreate = canRole(user, ["lawyer", "admin"]);

  const search = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setWarning(null);
    try {
      const response = await apiClient.searchRag(query);
      setResults(response.results);
      setWarning(response.warning ?? (response.results.length === 0 ? "Источник не найден, требуется проверка юриста." : null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить поиск");
    } finally {
      setLoading(false);
    }
  };

  const createSource = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const created = await apiClient.createRagSource({
        title,
        sourceType,
        fragment,
        category: "general",
      });
      setResults((current) => [created, ...current]);
      setTitle("");
      setFragment("");
      setWarning(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать источник");
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppShell title="Правовые источники" description="Панель RAG-источников, используемых для подготовки претензий и исков.">
      <div className="grid two">
        <section className="card stack">
          <h2 className="section-title">Поиск по источникам</h2>
          <form className="stack" onSubmit={search}>
            <input className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Например: договор поставки неустойка" required />
            <button className="btn" type="submit" disabled={loading}>
              {loading ? "Поиск..." : "Найти источники"}
            </button>
          </form>
          {warning ? <div className="status warning">{warning}</div> : null}
          {error ? <div className="status error">{error}</div> : null}
          <div className="list">
            {results.map((item) => (
              <article className="list-item" key={item.id}>
                <div className="stack">
                  <strong>{item.title}</strong>
                  <div className="muted">{item.fragment}</div>
                  <div className="muted">
                    {item.sourceType} / {item.category || "general"}
                  </div>
                </div>
                <span className="pill">score {item.score}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="card stack">
          <h2 className="section-title">Добавить источник</h2>
          {!canCreate ? <div className="status warning">Создание RAG-источников доступно только lawyer и admin.</div> : null}
          <form className="stack" onSubmit={createSource}>
            <input className="input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Название источника" disabled={!canCreate || creating} required />
            <select className="select" value={sourceType} onChange={(event) => setSourceType(event.target.value)} disabled={!canCreate || creating}>
              <option value="law">law</option>
              <option value="case_law">case_law</option>
              <option value="internal">internal</option>
            </select>
            <textarea className="textarea" value={fragment} onChange={(event) => setFragment(event.target.value)} placeholder="Фрагмент источника" disabled={!canCreate || creating} required />
            <button className="btn" type="submit" disabled={!canCreate || creating}>
              {creating ? "Сохранение..." : "Сохранить источник"}
            </button>
          </form>
        </section>
      </div>
    </AppShell>
  );
}
