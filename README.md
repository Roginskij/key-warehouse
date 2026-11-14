# KeyVerhaus

## Запуск (локально)

1. Запустить **Postgres.app** (база).
2. Бэкенд + почта:
   ```bash
   docker compose up -d --build
   ```
   (`--build` — чтобы подхватить свежий код бэкенда)
3. Фронтенд (приложение):
   ```bash
   cd frontend && pnpm dev
   ```
4. Сайт для клиентов (по желанию, в другом окне):
   ```bash
   cd frontend && pnpm dev:shop
   ```

## Где открывать

| Что | Адрес |
|---|---|
| Приложение | http://localhost:5173 |
| Сайт для клиентов | http://localhost:3000 |
| Админка | http://localhost:5173/admin |
| Письма (подтверждение, пароль) | http://localhost:8025 |
| API-документация | http://localhost:8000/docs |

Демо-аккаунт (склад, не админ): `cd backend && uv run python -m app.seed_demo` →
почта и пароль в `backend/dev-accounts.local.md`.
Показать демо-мастерскую на сайте: `uv run python -m app.seed_demo --shop`.

Подробнее: [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md), решения — [docs/decisions.md](docs/decisions.md).
