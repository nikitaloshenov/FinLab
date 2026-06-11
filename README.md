# FinLab

FinLab — backend-oriented fullstack fintech-проект для анализа MOEX-тикеров, списка наблюдения, ценовых алертов и проверки рыночных гипотез на исторических данных.

- Live demo: https://jirniydizainer.ru
- Swagger API: https://jirniydizainer.ru/docs
- GitHub: https://github.com/nikitaloshenov/FinLab

## Коротко

FinLab — production-like fullstack fintech pet-project с основным фокусом на backend, данные, API, PostgreSQL, миграции, аналитическую логику, Docker и CI.

Проект позволяет работать с MOEX-тикерами, вести список наблюдения, обновлять рыночные данные, создавать ценовые алерты и проверять гипотезы о реакции акций на решения ЦБ по ключевой ставке. Frontend здесь выступает как демонстрационный web-интерфейс для backend-фичей.

FinLab не предсказывает будущее, не дает инвестиционных рекомендаций и не является production trading system.

## Главные возможности

- список наблюдения MOEX-тикеров;
- загрузка и обновление рыночных данных через MOEX ISS API;
- свечной график по MOEX candles;
- таблица последних свечей;
- ценовые алерты;
- история срабатывания алертов;
- anonymous demo sessions без регистрации;
- Key Rate Impact Analyzer;
- сравнение реакции акции с benchmark;
- PostgreSQL persistence;
- Alembic migrations;
- CSV importer для исторических решений по ключевой ставке;
- Docker Compose запуск;
- Swagger API;
- backend tests и GitHub Actions CI.

## Key Rate Impact Analyzer

Главная аналитическая фича проекта — Key Rate Impact Analyzer.

Он отвечает на вопрос:

> Как выбранная акция исторически реагировала на похожие решения ЦБ по ключевой ставке?

Пользователь выбирает:

- тикер акции;
- сценарий ставки: снижение, повышение или сохранение;
- горизонты анализа: 1, 3 и 10 торговых дней;
- optional benchmark.

После этого backend:

- берет исторические решения ЦБ из таблицы `key_rate_decisions`;
- загружает дневные свечи MOEX;
- для каждого решения ищет первую торговую свечу с датой `>= decision_date`;
- берет `close` этой свечи как event price;
- считает доходность через 1/3/10 торговых дней;
- сравнивает результат с benchmark, если он выбран;
- возвращает summary, best horizon, confidence, skipped summary, horizon summary и event results.

Если свеча события или свеча горизонта отсутствует, событие или горизонт пропускается. Отсутствующие данные не заменяются нулем.

Это historical event-study, а не прогноз цены и не инвестиционная рекомендация.

## Anonymous Demo Sessions

В проекте нет регистрации и полноценной авторизации. Для demo-доступа используется anonymous browser session.

Как это работает:

- при первом заходе frontend создает session id;
- session id хранится в `localStorage`;
- frontend отправляет его в backend через заголовок `X-FinLab-Session-Id`;
- watchlist и alerts изолированы между разными браузерами/сессиями;
- если очистить `localStorage`, demo session будет потеряна;
- это не замена полноценной auth-системы, а легкий механизм для публичного demo.

## Стек

Backend:

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- pytest
- httpx

Frontend:

- React
- Vite
- JavaScript
- CSS
- SVG chart rendering

Infrastructure:

- Docker
- Docker Compose
- nginx-proxy / gateway на сервере
- HTTPS
- GitHub Actions CI

Data / market:

- MOEX ISS API
- curated key rate decisions dataset
- CSV importer

## Архитектура

Общий flow:

```text
Frontend -> API -> FastAPI routers -> services -> repositories -> PostgreSQL
                                      -> MOEX ISS API
```

Backend разделен на модули:

- `market` — тикеры, latest price, MOEX candles;
- `watchlist` — список наблюдения;
- `alerts` — ценовые алерты и история событий;
- `hypotheses` — аналитические гипотезы и Key Rate Impact Analyzer.

В модулях используется простое разделение слоев:

- `router.py` — HTTP endpoints;
- `service.py` — бизнес-логика;
- `repository.py` — работа с БД;
- `schemas.py` — Pydantic request/response models;
- `models.py` — SQLAlchemy models.

Аналитический engine Key Rate Impact Analyzer вынесен отдельно от router-слоя. Backend startup в Docker выполняет:

```text
wait postgres -> alembic upgrade head -> import key rate decisions -> uvicorn
```

## API Overview

Health:

- `GET /api/v1/health`
- `GET /api/v1/health/db`

Market:

- `GET /api/v1/market/tickers`
- `GET /api/v1/market/tickers/{secid}/moex`
- `POST /api/v1/market/tickers/{secid}/refresh`
- `GET /api/v1/market/tickers/{secid}/price`
- `GET /api/v1/market/tickers/{secid}/candles`

Watchlist:

- `GET /api/v1/watchlist`
- `POST /api/v1/watchlist/items`
- `DELETE /api/v1/watchlist/items/{secid}`
- `POST /api/v1/watchlist/refresh-prices`

Alerts:

- `GET /api/v1/alerts`
- `POST /api/v1/alerts`
- `POST /api/v1/alerts/{alert_id}/check`
- `POST /api/v1/alerts/check-active`
- `DELETE /api/v1/alerts/{alert_id}`
- `GET /api/v1/alerts/events`

Hypotheses:

- `POST /api/v1/hypotheses/analyze`
- `GET /api/v1/hypotheses/key-rate-events`
- `GET /api/v1/hypotheses/key-rate-decisions`
- `POST /api/v1/hypotheses/key-rate-impact/analyze`

## Локальный запуск через Docker Compose

```powershell
git clone https://github.com/nikitaloshenov/FinLab.git
cd FinLab
docker compose up --build
```

Локальные URL:

- Frontend: http://127.0.0.1:5173
- Backend: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

При старте backend Docker Compose ждет PostgreSQL, запускает Alembic migrations и импортирует curated key rate decisions dataset из `backend/app/data/key_rate_decisions_official.csv`. Importer использует upsert, поэтому повторный запуск не должен дублировать решения.

### Docker persistence

PostgreSQL хранит данные в named volume `finlab_postgres_data`.

```powershell
docker compose down
```

Останавливает контейнеры, но сохраняет данные БД. Watchlist, alerts и импортированные решения по ключевой ставке останутся доступны после следующего запуска.

```powershell
docker compose down -v
```

Останавливает контейнеры и удаляет volume. Это reset базы данных: watchlist и alerts станут пустыми. При следующем старте backend снова выполнит migrations и импортирует key rate decisions.

## Demo Deploy

Проект задеплоен на demo-домен:

- Frontend: https://jirniydizainer.ru
- Backend API: https://jirniydizainer.ru/api/v1
- Swagger: https://jirniydizainer.ru/docs

На demo-сервере проект работает через reverse proxy:

```text
https://jirniydizainer.ru -> frontend
https://jirniydizainer.ru/api/v1 -> backend API
https://jirniydizainer.ru/docs -> Swagger
```

Для такого режима frontend использует относительный API base:

```env
VITE_API_BASE_URL=/api/v1
```

Если frontend и backend находятся на разных origins, backend CORS настраивается через:

```env
BACKEND_CORS_ORIGINS=https://jirniydizainer.ru,https://www.jirniydizainer.ru
```

## Локальный запуск без Docker

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python scripts/import_key_rate_decisions.py --file app/data/key_rate_decisions_official.csv
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Тесты

Backend:

```powershell
cd backend
python -m pytest
```

Frontend build:

```powershell
cd frontend
npm run build
```

Backend покрыт тестами для:

- watchlist;
- alerts;
- anonymous sessions;
- Key Rate Impact Analyzer;
- MOEX client;
- CSV importer;
- API endpoints.

CI также запускает backend tests и frontend build.

## Документация

- [Project Context](PROJECT_CONTEXT.md)
- [Feature Roadmap](FEATURE_ROADMAP.md)
- [Key Rate Analyzer Spec](KEY_RATE_ANALYZER_SPEC.md)
- [Key Rate Dataset Spec](KEY_RATE_DATASET_SPEC.md)
- [Audit Log](AUDIT_LOG.md)

## Что проект демонстрирует

- проектирование backend API;
- модульную FastAPI-архитектуру;
- SQLAlchemy models и repository layer;
- Alembic migrations;
- PostgreSQL persistence;
- интеграцию с внешним market data API;
- обработку ошибок и structured API errors;
- аналитическую backend-логику;
- event-study подход на исторических данных;
- pytest и API integration tests;
- Docker startup flow;
- CI;
- frontend integration как демонстрационный слой.

## Ограничения

- проект не является production trading system;
- проект не является инвестиционной рекомендацией;
- historical analysis не доказывает причинность и не гарантирует будущую реакцию рынка;
- данные MOEX могут быть недоступны или отвечать с задержкой;
- anonymous sessions не заменяют полноценную авторизацию;
- публичный demo предназначен для демонстрации проекта, а не для реальных торговых решений;
- UI и аналитические сценарии продолжают развиваться.

## Roadmap

Ближайшие возможные направления:

- полноценная авторизация пользователей;
- сохраненные гипотезы;
- кэширование MOEX candles;
- screenshots и demo-flow в README;
- второй аналитический модуль;
- portfolio tracker;
- отдельная landing page.

## Автор

Никита Лощенов

- GitHub: https://github.com/nikitaloshenov/FinLab
- Telegram: https://t.me/JIRNIYDIZAINER
