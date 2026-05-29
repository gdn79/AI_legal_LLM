"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { useAuth } from "../../components/providers";

export default function LoginPage() {
  const router = useRouter();
  const { login, user } = useAuth();
  const [email, setEmail] = useState(user?.email ?? "initiator@example.com");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      await login({ email, password });
      router.push("/cases");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить вход");
    }
  };

  return (
    <main className="container">
      <div className="grid two">
        <section className="card">
          <h1 className="page-title">Вход в Legal Claim AI</h1>
          <p className="subtle">
            Локальный MVP-интерфейс для инициатора, юриста, руководителя, администратора и service agent.
            Юридически значимые действия подтверждаются backend-правилами и ролью юриста.
          </p>

          <form className="stack" onSubmit={onSubmit}>
            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                data-testid="login-email"
                className="input"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                autoComplete="email"
                required
              />
            </div>

            <div>
              <label className="label" htmlFor="password">
                Пароль
              </label>
              <input
                id="password"
                data-testid="login-password"
                className="input"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
                required
              />
            </div>

            {error ? <div className="status error">{error}</div> : null}

            <button className="btn" data-testid="login-submit" type="submit">
              Войти
            </button>
          </form>
        </section>

        <section className="card stack">
          <h2 className="section-title">Что уже доступно</h2>
          <div className="muted-box">
            <strong>Контрактный frontend</strong>
            <p className="subtle">
              UI работает с backend OpenAPI и в mock/manual режиме: логин, дела, документы, извлечение фактов,
              претензия, иск, RAG, чек-лист, дашборд, аудит и настройки.
            </p>
          </div>
          <div className="card-muted">
            <div className="label">Тестовые пользователи</div>
            <div className="stack">
              <span className="pill">initiator@example.com</span>
              <span className="pill">lawyer@example.com</span>
              <span className="pill">manager@example.com</span>
              <span className="pill">admin@example.com</span>
              <span className="pill">service-agent@example.com</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
