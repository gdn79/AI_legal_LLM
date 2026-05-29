"use client";

import { useEffect, useState } from "react";
import { AppShell } from "../../components/app-shell";
import { canRole, useAuth } from "../../components/providers";
import { EmptyState, ErrorState, LoadingState } from "../../components/states";
import { apiClient } from "../../lib/api-client";
import type { SettingItem } from "../../lib/types";

export default function SettingsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<SettingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const allowed = canRole(user, ["admin"]);

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    apiClient
      .listSettings()
      .then((result) => {
        if (active) {
          setItems(result);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить настройки");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [allowed]);

  const updateItem = async (key: string) => {
    const current = items.find((item) => item.key === key);
    if (!current) {
      return;
    }
    setSavingKey(key);
    setError(null);
    try {
      const updated = await apiClient.updateSetting(key, current.value, current.description);
      setItems((existing) => existing.map((item) => (item.key === key ? updated : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить настройку");
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <AppShell title="Настройки" description="Системные параметры и параметры интеграции.">
      {!allowed ? <EmptyState title="Настройки недоступны" description="Эта страница доступна только роли admin." /> : null}
      {allowed && loading ? <LoadingState label="Загружаем настройки..." /> : null}
      {allowed && error ? <ErrorState title="Не удалось загрузить настройки" message={error} /> : null}
      {allowed && !loading && !error ? (
        <div className="grid two">
          <section className="card stack">
            <h2 className="section-title">Интеграция</h2>
            <div className="card-muted">
              <div className="label">Backend URL</div>
              <code>{process.env.NEXT_PUBLIC_API_URL ?? "not configured"}</code>
            </div>
            <div className="muted-box">
              Настройки API берутся из `NEXT_PUBLIC_API_URL`. Если backend недоступен, frontend может работать в fallback-режиме.
            </div>
          </section>

          <section className="card stack">
            <h2 className="section-title">Профиль</h2>
            <div className="card-muted">
              <div className="label">Пользователь</div>
              <div>{user?.email ?? "guest"}</div>
              <div className="muted">{user?.role ?? "no role"}</div>
            </div>
          </section>

          <section className="card stack" style={{ gridColumn: "1 / -1" }}>
            <h2 className="section-title">Системные параметры</h2>
            {items.length === 0 ? (
              <div className="muted-box">Настройки пока не заданы.</div>
            ) : (
              <div className="list">
                {items.map((item) => (
                  <article className="list-item" key={item.key}>
                    <div className="stack" style={{ flex: 1 }}>
                      <strong>{item.key}</strong>
                      <input
                        className="input"
                        value={item.value}
                        onChange={(event) =>
                          setItems((current) =>
                            current.map((currentItem) =>
                              currentItem.key === item.key ? { ...currentItem, value: event.target.value } : currentItem,
                            ),
                          )
                        }
                      />
                      <input
                        className="input"
                        value={item.description}
                        onChange={(event) =>
                          setItems((current) =>
                            current.map((currentItem) =>
                              currentItem.key === item.key ? { ...currentItem, description: event.target.value } : currentItem,
                            ),
                          )
                        }
                      />
                    </div>
                    <button className="btn" type="button" onClick={() => updateItem(item.key)} disabled={savingKey === item.key}>
                      {savingKey === item.key ? "Сохранение..." : "Сохранить"}
                    </button>
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
