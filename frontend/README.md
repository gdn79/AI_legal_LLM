# Frontend MVP

Минимальный frontend для Local Legal LLM / Legal Claim AI на Next.js + TypeScript.

## Запуск

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Скрипты

```bash
npm run dev
npm run build
npm run start
npm run typecheck
```

## Контракт с backend

Frontend использует `NEXT_PUBLIC_API_URL`.
Для локальной интеграции с backend укажите:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Если переменная не задана, UI работает на локальном mock-fallback.

## Demo login

Готовые локальные пользователи:

```text
admin@example.com
lawyer@example.com
manager@example.com
initiator@example.com
```

Пароль для локальной разработки: `ChangeMe123!`
