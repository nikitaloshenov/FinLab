# FinLab — Market Watchlist & Alerts

FinLab — учебное fullstack-приложение для мониторинга MOEX-тикеров. Проект позволяет вести watchlist, получать рыночные данные через MOEX ISS API, сохранять цены в PostgreSQL, создавать price alerts и смотреть историю срабатываний alert'ов через React frontend.

Проект находится в MVP-стадии, но уже имеет рабочий backend, frontend, PostgreSQL, Alembic migrations, batch endpoints и первые tests.

## Стек технологий

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pytest
- httpx
- Docker для PostgreSQL

### Frontend

- React
- Vite
- JavaScript
- CSS

## Возможности проекта

- Добавить тикер в watchlist.
- Удалить тикер из watchlist.
- Обновить цену одного тикера.
- Обновить цены всех тикеров через backend batch endpoint.
- Создать price alert.
- Проверить один alert.
- Проверить все активные alerts через backend batch endpoint.
- Посмотреть историю alert events.
- Использовать retry/timeout для MOEX client.
- Запускать первые backend tests.

## Архитектура проекта

```text
backend/app/core
backend/app/modules/market
backend/app/modules/watchlist
backend/app/modules/alerts
backend/app/shared
frontend/src/pages
frontend/src/features
frontend/src/shared/api
```

Backend организован по модульному принципу:

- `router.py` — HTTP endpoints.
- `service.py` — бизнес-логика.
- `repository.py` — работа с базой данных.
- `schemas.py` — Pydantic-схемы request/response.
- `models.py` — SQLAlchemy-модели.

## Основные API endpoints

### Health

- `GET /api/v1/health`
- `GET /api/v1/health/db`

### Market

- `GET /api/v1/market/tickers`
- `GET /api/v1/market/tickers/{secid}/moex`
- `POST /api/v1/market/tickers/{secid}/refresh`
- `GET /api/v1/market/tickers/{secid}/price`

### Watchlist

- `GET /api/v1/watchlist`
- `POST /api/v1/watchlist/items`
- `DELETE /api/v1/watchlist/items/{secid}`
- `POST /api/v1/watchlist/refresh-prices`

### Alerts

- `GET /api/v1/alerts`
- `POST /api/v1/alerts`
- `POST /api/v1/alerts/{alert_id}/check`
- `POST /api/v1/alerts/check-active`
- `DELETE /api/v1/alerts/{alert_id}`
- `GET /api/v1/alerts/events`

## Переменные окружения

Пример переменных окружения находится в корне проекта:

```text
.env.example
```

`.env.example` служит общим шаблоном переменных для проекта. Для локального запуска backend нужно создать `backend/.env` на основе корневого `.env.example`. Реальные `.env`-файлы не нужно коммитить.

Frontend может работать без `frontend/.env`: для `VITE_API_BASE_URL` есть fallback на локальный backend. При необходимости `VITE_API_BASE_URL` можно задать в `frontend/.env` или в окружении сборки.

Основные переменные:

- `APP_NAME` — название приложения.
- `APP_ENV` — окружение приложения.
- `API_V1_PREFIX` — префикс backend API.
- `DATABASE_URL` — строка подключения к PostgreSQL.
- `MOEX_BASE_URL` — базовый URL MOEX ISS API.
- `MOEX_DEFAULT_ENGINE` — engine MOEX по умолчанию.
- `MOEX_DEFAULT_MARKET` — market MOEX по умолчанию.
- `MOEX_DEFAULT_BOARD` — board MOEX по умолчанию.
- `MOEX_TIMEOUT_SECONDS` — timeout HTTP-запросов к MOEX.
- `MOEX_RETRY_ATTEMPTS` — количество попыток запроса к MOEX.
- `MOEX_RETRY_DELAY_SECONDS` — пауза между попытками.
- `BACKEND_CORS_ORIGINS` — разрешенные origins для CORS.
- `VITE_API_BASE_URL` — базовый URL backend API для frontend.

## Локальный запуск

### 1. Поднять PostgreSQL

```powershell
docker compose up -d postgres
```

### 2. Запустить backend

```powershell
cd backend
Copy-Item ..\.env.example .\.env
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000

Swagger: http://127.0.0.1:8000/docs

### 3. Запустить frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Тесты

```powershell
cd backend
python -m pytest
```

Сейчас тестами покрыто:

- alert condition logic;
- alert messages;
- MOEX retry/invalid JSON handling;
- batch service behavior.

## Текущий статус

Проект находится в MVP-стадии. Уже реализованы рабочий backend, frontend, PostgreSQL, migrations, batch endpoints и первые tests. Проект не является production-ready.

## Roadmap

### Ближайшие улучшения

- GitHub Actions для `pytest` и frontend build.
- Разнести `MarketPage.jsx` на компоненты.
- Добавить централизованные exception handlers.
- Расширить backend tests.

### Позже

- История цен по тикеру на frontend.
- Графики цен.
- Background refresh.
- Telegram/email notifications.
- Docker для backend/frontend.
- Soft delete для alerts.

## Важные ограничения

- Это учебный проект.
- Пока нет авторизации.
- Пока нет background jobs.
- Пока нет production deploy.
- Docker сейчас используется только для PostgreSQL.
