КОНТЕКСТ ПРОЕКТА ДЛЯ CODEX

Название проекта: FinLab.

Это учебный fullstack-проект, но код должен быть похож на нормальный рабочий backend/frontend проект. Сейчас основной модуль проекта — Market Watchlist & Alerts.

Проект состоит из backend и frontend.

Backend:
- Python
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic
- Docker пока используется только для PostgreSQL
- папка backend/

Frontend:
- Vite
- React
- обычный CSS
- папка frontend/

Главная цель проекта:
Сделать небольшую систему мониторинга рынка, где пользователь может:
- добавлять тикеры MOEX в watchlist;
- получать данные по тикерам из MOEX ISS API;
- сохранять тикеры и цены в PostgreSQL;
- хранить последнюю цену;
- создавать price alerts;
- вручную проверять alerts;
- видеть историю срабатывания alerts;
- пользоваться всем этим через React frontend.

АРХИТЕКТУРА BACKEND

backend/app/
- core/
  - config.py — настройки приложения из .env
  - database.py — SQLAlchemy engine/session/Base
- modules/
  - market/
    - models.py
    - schemas.py
    - repository.py
    - service.py
    - router.py
    - moex_client.py
  - watchlist/
    - models.py
    - schemas.py
    - repository.py
    - service.py
    - router.py
  - alerts/
    - models.py
    - schemas.py
    - repository.py
    - service.py
    - router.py
  - notifications/
    - пока почти не используется, зарезервировано под будущие Telegram/email уведомления
- shared/
  - errors.py
  - pagination.py
- main.py — FastAPI app, подключение routers, CORS, health endpoints

Правила backend-архитектуры:
- router.py отвечает только за HTTP endpoints.
- service.py отвечает за бизнес-логику.
- repository.py отвечает за запросы к базе данных.
- schemas.py содержит Pydantic request/response схемы.
- models.py содержит SQLAlchemy модели.
- Не класть бизнес-логику напрямую в router.py, кроме совсем маленьких вещей.
- Не делать огромные рефакторы без отдельного запроса.
- Все изменения делать маленькими и осознанными.
- Не делать коммит автоматически.
- После изменений показать diff или кратко объяснить, какие файлы изменились и почему.

БАЗА ДАННЫХ

PostgreSQL запущен через Docker.
Docker compose service называется postgres.
Таблицы уже созданы через Alembic migrations.

Основные сущности:

Market:
- Ticker
- Price
- TickerLatestPrice

Watchlist:
- WatchlistItem

Alerts:
- Alert
- AlertEvent

MARKET MODULE

Market отвечает за тикеры, цены и работу с MOEX.

MOEX client получает данные из MOEX ISS API.

Refresh тикера должен:
- получить данные из MOEX;
- создать тикер, если его еще нет;
- сохранить цену в таблицу prices;
- обновить ticker_latest_prices.

Для цен использовать Decimal, не float.

Основные endpoint’ы:
- GET /api/v1/market/tickers
- GET /api/v1/market/tickers/{secid}/moex
- POST /api/v1/market/tickers/{secid}/refresh
- GET /api/v1/market/tickers/{secid}/price

WATCHLIST MODULE

Watchlist отвечает за список отслеживаемых тикеров.

Основные endpoint’ы:
- GET /api/v1/watchlist
- POST /api/v1/watchlist/items
- DELETE /api/v1/watchlist/items/{secid}
- POST /api/v1/watchlist/refresh-prices

Поведение:
- GET /api/v1/watchlist возвращает список тикеров в watchlist.
- POST /api/v1/watchlist/items добавляет тикер в watchlist.
- Если тикера еще нет в базе, backend должен сходить в MOEX, создать тикер и сохранить цену.
- DELETE /api/v1/watchlist/items/{secid} удаляет тикер из watchlist, но не удаляет сам тикер и историю цен из базы.
- POST /api/v1/watchlist/refresh-prices обновляет цены всех тикеров из watchlist.
- Batch refresh должен продолжать работу, даже если один тикер упал.
- Ответ batch refresh должен содержать total, updated, failed и подробности по каждому тикеру.

ALERTS MODULE

Alerts отвечает за price alerts.

Основные endpoint’ы:
- GET /api/v1/alerts
- POST /api/v1/alerts
- POST /api/v1/alerts/{alert_id}/check
- POST /api/v1/alerts/check-active
- DELETE /api/v1/alerts/{alert_id}
- GET /api/v1/alerts/events

Условия alert:
- above: current_price >= target_price
- below: current_price <= target_price

Поведение:
- Alert создается для тикера и целевой цены.
- Если тикера нет в базе, backend может подтянуть его через MOEX.
- При срабатывании alert:
  - создается AlertEvent;
  - alert становится inactive;
  - заполняется triggered_at.
- Inactive alert не должен срабатывать повторно.
- POST /api/v1/alerts/check-active проверяет все активные alerts.
- Batch check должен продолжать работу, даже если один alert упал.
- Ответ batch check должен содержать total, checked, triggered, failed и item details.

АРХИТЕКТУРА FRONTEND

frontend/src/
- main.jsx
- App.jsx
- styles.css
- pages/
  - MarketPage.jsx
- shared/api/
  - client.js
- features/
  - watchlist/api.js
  - market/api.js
  - alerts/api.js

Frontend сейчас находится в MVP-состоянии.
MarketPage.jsx пока большой, это нормально.
Пока не дробить MarketPage.jsx на компоненты без отдельного запроса.

Frontend умеет:
- показывать watchlist;
- добавлять тикеры;
- удалять тикеры;
- обновлять цену одного тикера;
- обновлять цены всего watchlist;
- показывать alerts;
- создавать alerts;
- проверять один alert;
- проверять все активные alerts;
- показывать alert events.

Frontend должен использовать backend batch endpoints:
- Refresh all prices должен вызывать один endpoint:
  POST /api/v1/watchlist/refresh-prices
- Check all active alerts должен вызывать один endpoint:
  POST /api/v1/alerts/check-active

Одиночные кнопки могут остаться как есть:
- Refresh одного тикера вызывает POST /api/v1/market/tickers/{secid}/refresh
- Check одного alert вызывает POST /api/v1/alerts/{alert_id}/check

Frontend должен показывать понятные сообщения:
- сколько тикеров обновлено;
- сколько ошибок;
- какие тикеры не обновились, если backend вернул failed items;
- сколько alert’ов проверено;
- сколько alert’ов сработало;
- какие alert’ы упали, если backend вернул failed items.

UI:
- Используется обычный CSS.
- Не добавлять Tailwind, MUI, shadcn и другие UI-библиотеки без отдельного запроса.
- Сохранять текущий темный стиль.
- Не делать карточки компактнее без отдельного запроса.
- Визуальный стиль сейчас устраивает.

КОМАНДЫ

Backend:
cd backend
python -m uvicorn app.main:app --reload

Frontend:
cd frontend
npm run dev

Docker/PostgreSQL:
docker compose up -d postgres
docker ps

Git:
Не делать коммит автоматически.
Пользователь сам выполнит:
git status
git add .
git commit -m "message"

ОГРАНИЧЕНИЯ

- Не редактировать .env без отдельного запроса.
- Не добавлять node_modules в Git.
- Не трогать .venv.
- Не переписывать весь проект.
- Не добавлять авторизацию пока.
- Не добавлять Docker для backend/frontend пока.
- Не добавлять Telegram notifications пока.
- Не добавлять background tasks пока.
- Не делать большие архитектурные изменения без согласования.
- Если задача неясна, лучше уточнить.
- Предпочитать маленькие изменения.
- После изменения объяснять, какие файлы изменены и почему.

БЛИЖАЙШИЕ ВОЗМОЖНЫЕ ЗАДАЧИ

1. Улучшить надежность MOEX client:
   - timeout 15 секунд;
   - 2 попытки всего;
   - пауза 0.5 секунды между попытками;
   - если обе попытки упали, выбрасывать MoexClientError с понятным сообщением.

2. Улучшить frontend-сообщения для batch operations:
   - если batch refresh частично упал, показать какие тикеры не обновились;
   - если batch alert check частично упал, показать какие alerts упали.

3. Добавить первые backend tests:
   - тест is_alert_triggered;
   - тест build_alert_message;
   - тест batch summary logic.

4. Позже разрезать MarketPage.jsx на компоненты:
   - WatchlistSection
   - AlertsSection
   - AlertEventsSection

5. Позже добавить notifications/background tasks.

ВАЖНЫЙ СТИЛЬ РАБОТЫ

Проект пишется поэтапно.
Не нужно сразу делать идеально.
Сначала рабочий MVP, потом улучшение архитектуры.
Если можно сделать маленькое безопасное изменение — делай маленькое.
Если изменение большое — сначала предложи план и дождись подтверждения.