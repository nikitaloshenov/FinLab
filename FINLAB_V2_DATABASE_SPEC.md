# FinLab v2 Database Specification

Документ описывает целевую архитектуру базы данных FinLab v2.

Это не миграция и не финальный SQL-дизайн. Цель документа — зафиксировать направление развития БД перед проектированием Alembic migrations, SQLAlchemy models и новой версии аналитического слоя.

## 1. Цель БД v2

FinLab v2 должен перестать быть просто dashboard вокруг тикеров и стать backend/product платформой для historical event-study анализа российского фондового рынка.

Целевая логика:

```text
событие -> рынок -> сектор -> акция -> историческая реакция -> сравнение с benchmark
```

База данных должна поддерживать:

- нормализованный справочник эмитентов, инструментов, секторов и benchmarks;
- хранение исторических свечей как аналитического market data layer;
- хранение событий разных типов, а не только решений по ключевой ставке;
- воспроизводимые study runs;
- сохранение event-level и horizon-level результатов анализа;
- будущие аналитические модули: инфляция, валютные шоки, нефть, дивидендные гэпы;
- будущий слой операционных, секторных и финансовых метрик компаний.

Главная идея v2: аналитика не должна каждый раз зависеть только от live-запросов к MOEX. Важные рыночные данные и результаты исследования должны быть воспроизводимы.

## 2. Главные принципы проектирования

1. Не сносить БД при изменениях.

   Все изменения должны идти через маленькие Alembic migrations. Старые таблицы нельзя удалять сразу, если от них зависит live demo.

2. Разделять типы данных.

   В БД должны быть разные слои:

   - user/demo data;
   - reference data;
   - market data;
   - event data;
   - study data;
   - future metrics data.

3. Не привязывать аналитику только к key rate.

   Key Rate Impact Analyzer должен стать первым use case поверх общего event-study слоя, а не единственным форматом данных.

4. Разделять issuer и instrument.

   Компания и торгуемый инструмент — разные сущности. Это важно для SBER/SBERP, облигаций, индексов, депозитарных расписок и будущих метрик.

5. Не хранить секторные метрики отдельными колонками под каждый сектор.

   Метрики должны быть описаны через catalog/observations, иначе БД быстро станет негибкой.

6. Хранить source provenance.

   Для данных MOEX, решений ЦБ, импортированных CSV и будущих источников нужно знать источник, дату загрузки и, по возможности, checksum.

7. Не ломать live demo большим refactor.

   Новые таблицы должны добавляться параллельно, а существующие watchlist/alerts/key rate API переводиться постепенно.

## 3. Слои данных

### A. User / Demo Layer

Назначение: хранить пользовательское состояние demo-приложения.

Текущие сущности:

- demo sessions;
- watchlist items;
- alerts;
- alert events.

В v2 этот слой можно оставить максимально простым. Он не должен смешиваться с market/reference/event data.

### B. Reference Layer

Назначение: описывать устойчивые справочники рынка.

Сущности:

- `issuers`;
- `instruments`;
- `sectors`;
- `issuer_sector_history`;
- `benchmarks`;
- `data_sources`.

Этот слой отвечает на вопросы:

- какая компания стоит за тикером;
- к какому сектору относится компания;
- какой инструмент является акцией, индексом или benchmark;
- из какого источника пришли данные.

### C. Market Data Layer

Назначение: хранить рыночные данные, нужные для анализа.

Сущности:

- `price_candles`;
- `latest_prices`;
- `ingestion_runs`.

В текущем проекте latest price уже есть через `ticker_latest_prices`, а candles берутся из MOEX live. Для v2 daily candles должны стать сохраняемыми данными.

### D. Event Layer

Назначение: хранить события, вокруг которых строится event-study.

Сущности:

- `event_types`;
- `events`;
- `event_values`.

Примеры событий:

- решение ЦБ по ключевой ставке;
- публикация инфляции;
- валютный шок;
- резкое движение нефти;
- дивидендный гэп;
- корпоративное событие.

### E. Study Layer

Назначение: хранить параметры и результаты аналитических запусков.

Сущности:

- `study_runs`;
- `study_run_events`;
- `study_event_results`;
- `study_horizon_summary`.

Этот слой нужен, чтобы результат анализа можно было воспроизвести, сравнить, показать в UI и протестировать.

### F. Future Metrics Layer

Назначение: будущая база для операционных, секторных и финансовых метрик.

Сущности:

- `reporting_periods`;
- `metrics_catalog`;
- `metric_observations`.

Этот слой не обязателен для первой реализации v2. `reporting_periods`, `metrics_catalog` и `metric_observations` остаются future-ready частью спецификации, но их лучше не включать в первую обязательную миграцию, если нет времени и стабильных источников данных.

## 4. Issuer vs Instrument

Это одно из самых важных разделений в v2.

`issuer` / company — это эмитент или компания.

`instrument` — это конкретный торгуемый инструмент.

Пример:

- ПАО Сбербанк — issuer;
- `SBER` — обыкновенная акция;
- `SBERP` — привилегированная акция;
- обе бумаги могут относиться к одному issuer.

Почему это важно:

- price candles относятся к instrument;
- watchlist обычно хранит instrument;
- alerts обычно работают по instrument;
- операционные и финансовые метрики чаще относятся к issuer;
- секторная принадлежность чаще относится к issuer, а не к отдельному ticker;
- один issuer может иметь несколько instruments.

Для v2 фиксируется основной вариант: использовать `issuer_sector_history`, а не `instrument_sector_history`.

Причина: сектор обычно относится к компании/эмитенту, а не к конкретному тикеру. `SBER` и `SBERP` могут быть разными инструментами одного issuer, но сектор у них общий.

Если позже появятся исключения, где конкретный instrument должен иметь отличную классификацию, можно добавить instrument-level sector override отдельной таблицей. В первую реализацию v2 это не входит.

## 5. Описание таблиц

### 5.1 `issuers`

Назначение: справочник эмитентов/компаний.

Ключевые поля:

- `id`;
- `name`;
- `short_name`;
- `country`;
- `website nullable`;
- `is_active`;
- `created_at`;
- `updated_at`.

Связи:

- one-to-many с `instruments`;
- one-to-many с `issuer_sector_history`;
- one-to-many с будущими `metric_observations`.

Уникальные ограничения:

- желательно unique по нормализованному `name` или внешнему issuer code, если такой источник будет добавлен.

Индексы:

- `ix_issuers_name`;
- `ix_issuers_is_active`.

Типы:

- даты: timezone-aware `DateTime`;
- `is_active`: boolean.

### 5.2 `instruments`

Назначение: справочник торгуемых инструментов.

Ключевые поля:

- `id`;
- `issuer_id nullable`;
- `secid`;
- `name`;
- `short_name`;
- `asset_type`;
- `board`;
- `market`;
- `engine`;
- `currency`;
- `lot_size nullable`;
- `isin nullable`;
- `is_active`;
- `created_at`;
- `updated_at`.

Связи:

- many-to-one к `issuers`;
- one-to-many к `price_candles`;
- one-to-many к `latest_prices`;
- optional one-to-many к `benchmarks`.

Уникальные ограничения:

- unique `(engine, market, board, secid)`;
- optional unique `isin`, если значение не null и надежно заполнено.

Индексы:

- `ix_instruments_secid`;
- `ix_instruments_asset_type`;
- `ix_instruments_issuer_id`;
- `ix_instruments_is_active`.

Типы:

- `lot_size`: integer или Numeric, если понадобится дробность;
- `currency`: string;
- `asset_type`: string или enum-like check constraint.

### 5.3 `sectors`

Назначение: справочник секторов.

Ключевые поля:

- `id`;
- `code`;
- `name`;
- `description nullable`;
- `is_active`.

Связи:

- one-to-many с `issuer_sector_history`;
- optional one-to-many с `benchmarks`;
- optional one-to-many с future `metrics_catalog`.

Уникальные ограничения:

- unique `code`;
- unique `name` желательно, но не обязательно.

Индексы:

- `ix_sectors_code`;
- `ix_sectors_is_active`.

### 5.4 `issuer_sector_history`

Назначение: история секторной принадлежности issuer.

Ключевые поля:

- `id`;
- `issuer_id`;
- `sector_id`;
- `valid_from`;
- `valid_to nullable`;
- `source_id nullable`.

Связи:

- many-to-one к `issuers`;
- many-to-one к `sectors`;
- many-to-one к `data_sources`.

Уникальные ограничения:

- желательно unique `(issuer_id, sector_id, valid_from)`;
- желательно не допускать пересекающиеся интервалы для одного issuer на уровне бизнес-валидации.

Индексы:

- `ix_issuer_sector_history_issuer_valid`;
- `ix_issuer_sector_history_sector_id`;
- `ix_issuer_sector_history_valid_from`.

Комментарий:

Для MVP можно считать сектор текущим, но структура с history позволит не переделывать БД позже.

### 5.5 `benchmarks`

Назначение: описание market/sector/instrument benchmarks.

Ключевые поля:

- `id`;
- `code`;
- `name`;
- `benchmark_type`;
- `instrument_id nullable`;
- `sector_id nullable`;
- `description nullable`;
- `is_active`.

Связи:

- optional many-to-one к `instruments`;
- optional many-to-one к `sectors`.

Уникальные ограничения:

- unique `code`.

Индексы:

- `ix_benchmarks_type`;
- `ix_benchmarks_instrument_id`;
- `ix_benchmarks_sector_id`;
- `ix_benchmarks_is_active`.

Комментарий:

`benchmark_type` может принимать значения:

- `market`;
- `sector`;
- `instrument`;
- `custom`.

Для текущего проекта важно явно не путать `MOEX` как акцию Московской биржи и индексный benchmark рынка.

Решение для v2: market index вроде IMOEX хранится как отдельный `instrument` с `asset_type = index`, а `benchmarks.instrument_id` ссылается на этот instrument. Это позволяет отличать:

- `MOEX` — акция Московской биржи;
- `IMOEX` — рыночный индекс / market benchmark.

### 5.6 `data_sources`

Назначение: provenance layer для данных.

Ключевые поля:

- `id`;
- `code`;
- `name`;
- `source_type`;
- `url nullable`;
- `license_note nullable`;
- `loaded_at nullable`;
- `checksum nullable`.

Связи:

- может использоваться в `price_candles`;
- `events`;
- `issuer_sector_history`;
- `metric_observations`;
- `ingestion_runs`.

Уникальные ограничения:

- unique `code`;
- optional unique `checksum` не нужен глобально, потому разные sources могут иметь одинаковые checksum.

Индексы:

- `ix_data_sources_code`;
- `ix_data_sources_source_type`.

Комментарий:

`source_type` может быть:

- `moex`;
- `cbr`;
- `manual_csv`;
- `official_page`;
- `computed`.

### 5.7 `price_candles`

Назначение: сохраненные OHLCV-свечи по instrument.

Ключевые поля:

- `id`;
- `instrument_id`;
- `interval`;
- `begin_at`;
- `trading_date`;
- `open`;
- `high`;
- `low`;
- `close`;
- `volume`;
- `value nullable`;
- `source_id nullable`;
- `ingestion_run_id nullable`;
- `created_at`.

Связи:

- many-to-one к `instruments`;
- optional many-to-one к `data_sources`;
- optional many-to-one к `ingestion_runs`.

Уникальные ограничения:

- unique `(instrument_id, interval, begin_at)`.

Важные индексы:

- `ix_price_candles_instrument_interval_begin_at`;
- `ix_price_candles_instrument_interval_trading_date`;
- `ix_price_candles_begin_at`;
- optional `ix_price_candles_interval_begin_at`.

Почему нужен unique `(instrument_id, interval, begin_at)`:

- MOEX pagination/chunking может вернуть пересекающиеся свечи;
- повторный import не должен создавать дубли;
- event-study должен иметь ровно одну свечу инструмента на интервал и дату/время;
- upsert становится простым и безопасным.

Типы:

- `open`, `high`, `low`, `close`: `Numeric(18, 6)` или точнее;
- `volume`: `Numeric(24, 6)` или `BigInteger`, если гарантированно целое;
- `value`: `Numeric(24, 6)`;
- `begin_at`: timezone-aware `DateTime`;
- `trading_date`: `Date`.

Комментарий:

Для MVP v2 можно начать только с `interval='1d'`.

Для daily candles `begin_at` можно нормализовать к началу торгового дня или к дате свечи в выбранной timezone. `trading_date` нужен отдельно, чтобы event-study мог удобно искать торговые дни: D+1, D+3, D+10, D+20.

`source_id` отвечает на вопрос "откуда данные". `ingestion_run_id` отвечает на вопрос "какой конкретный импорт/загрузка принес эти строки".

### 5.8 `latest_prices`

Назначение: быстрый current/latest price layer.

Ключевые поля:

- `id`;
- `instrument_id`;
- `price`;
- `previous_price nullable`;
- `source_id nullable`;
- `received_at`;
- `market_time nullable`.

Связи:

- many-to-one к `instruments`;
- optional many-to-one к `data_sources`.

Уникальные ограничения:

- unique `instrument_id`.

Индексы:

- `ix_latest_prices_instrument_id`;
- `ix_latest_prices_received_at`.

Комментарий:

Текущая таблица `ticker_latest_prices` может быть постепенно заменена или связана с `latest_prices`.

### 5.9 `ingestion_runs`

Назначение: учет загрузок данных.

Ключевые поля:

- `id`;
- `source_id`;
- `ingestion_type`;
- `status`;
- `started_at`;
- `finished_at nullable`;
- `params_json nullable`;
- `rows_loaded`;
- `rows_failed`;
- `error_message nullable`.

Связи:

- many-to-one к `data_sources`.

Индексы:

- `ix_ingestion_runs_source_started`;
- `ix_ingestion_runs_status`.

JSONB:

- `params_json` лучше хранить как JSONB.

### 5.10 `event_types`

Назначение: справочник типов событий.

Ключевые поля:

- `id`;
- `code`;
- `name`;
- `description`;
- `default_source_id nullable`.

Связи:

- one-to-many с `events`;
- optional many-to-one к `data_sources`.

Уникальные ограничения:

- unique `code`.

Примеры `code`:

- `key_rate_decision`;
- `inflation_release`;
- `fx_shock`;
- `oil_shock`;
- `dividend_gap`.

### 5.11 `events`

Назначение: конкретные события для event-study.

Ключевые поля:

- `id`;
- `event_type_id`;
- `source_event_id nullable`;
- `event_date`;
- `event_datetime nullable`;
- `title`;
- `direction nullable`;
- `importance nullable`;
- `source_id nullable`;
- `created_at`.

Связи:

- many-to-one к `event_types`;
- optional many-to-one к `data_sources`;
- one-to-many к `event_values`;
- one-to-many к `study_run_events`;
- one-to-many к `study_event_results`.

Уникальные ограничения:

- для key rate можно unique `(event_type_id, event_date)`;
- для общего слоя лучше unique `(event_type_id, event_date, title)` или source-specific external id, если появится.
- если источник дает стабильный внешний id события, желательно unique `(source_id, source_event_id)`.

Индексы:

- `ix_events_type_date`;
- `ix_events_date`;
- `ix_events_direction`;
- `ix_events_source_id`;
- `ix_events_source_event_id`.

Комментарий:

`direction` можно использовать для `rate_cut`, `rate_hike`, `rate_hold`, но не все event types имеют direction.

`source_event_id` нужен для повторных importer runs. Если ЦБ, MOEX или другой источник дает уникальный id события, его лучше сохранить, чтобы не создавать дубли по title/date эвристикам.

### 5.12 `event_values`

Назначение: гибкое хранение значений события.

Ключевые поля:

- `id`;
- `event_id`;
- `key`;
- `numeric_value nullable`;
- `text_value nullable`;
- `unit nullable`.

Связи:

- many-to-one к `events`.

Уникальные ограничения:

- unique `(event_id, key)`.

Индексы:

- `ix_event_values_event_id`;
- `ix_event_values_key`.

Типы:

- `numeric_value`: `Numeric`;
- `text_value`: text.

Примеры:

- `rate_before = 16.00`;
- `rate_after = 18.00`;
- `change_bps = 200`;
- `inflation_yoy = 7.40`;
- `oil_price_change_percent = -5.20`.

### 5.13 `study_runs`

Назначение: один запуск аналитического исследования.

Ключевые поля:

- `id`;
- `study_type`;
- `main_instrument_id`;
- `sector_id nullable`;
- `market_benchmark_id nullable`;
- `sector_benchmark_id nullable`;
- `params_json`;
- `methodology_version`;
- `data_version nullable`;
- `data_cutoff_at nullable`;
- `status`;
- `created_at`;
- `completed_at nullable`.

Связи:

- many-to-one к `instruments`;
- optional many-to-one к `sectors`;
- optional many-to-one к `benchmarks`;
- one-to-many к `study_run_events`;
- one-to-many к `study_event_results`;
- one-to-many к `study_horizon_summary`.

Индексы:

- `ix_study_runs_study_type_created`;
- `ix_study_runs_main_instrument_id`;
- `ix_study_runs_status`;

JSONB:

- `params_json` должен быть JSONB.

Комментарий:

`params_json` фиксирует horizons, filters, event type, direction, date range, benchmark settings.

`methodology_version` фиксирует версию расчетной логики. Это важно, потому что один и тот же набор событий может дать другой результат после изменения правил поиска event candle, benchmark или классификации эффекта.

`data_cutoff_at` показывает, на каком состоянии данных был сделан расчет. Например, study run мог быть построен по candles и events, доступным на конкретный момент времени.

### 5.14 `study_run_events`

Назначение: события, попавшие в конкретный study run.

Ключевые поля:

- `id`;
- `study_run_id`;
- `event_id`;
- `status`;
- `skipped_reason nullable`.

Связи:

- many-to-one к `study_runs`;
- many-to-one к `events`.

Уникальные ограничения:

- unique `(study_run_id, event_id)`.

Индексы:

- `ix_study_run_events_run_id`;
- `ix_study_run_events_event_id`;
- `ix_study_run_events_status`.

### 5.15 `study_event_results`

Назначение: результат анализа по одному событию, одному instrument и одному horizon.

Ключевые поля:

- `id`;
- `study_run_id`;
- `event_id`;
- `instrument_id`;
- `horizon_trading_days`;
- `event_price`;
- `horizon_price`;
- `return_percent`;
- `market_return_percent nullable`;
- `sector_return_percent nullable`;
- `relative_to_market_percent nullable`;
- `relative_to_sector_percent nullable`;
- `status`;
- `skipped_reason nullable`.

Связи:

- many-to-one к `study_runs`;
- many-to-one к `events`;
- many-to-one к `instruments`.

Уникальные ограничения:

- unique `(study_run_id, event_id, instrument_id, horizon_trading_days)`.

Индексы:

- `ix_study_event_results_run_horizon`;
- `ix_study_event_results_event_id`;
- `ix_study_event_results_instrument_id`;
- `ix_study_event_results_status`;

Типы:

- price fields: `Numeric(18, 6)`;
- percent fields: `Numeric(12, 6)` или `Numeric(10, 4)`.

Комментарий:

Если данных нет, не нужно писать fake zero. Поля return/price могут быть null, а `status/skipped_reason` объясняют причину.

`horizon_trading_days` означает именно торговые дни, а не календарные. Например, значение `10` означает десятую доступную торговую свечу после event candle.

### 5.16 `study_horizon_summary`

Назначение: агрегированный результат study run по horizon.

Ключевые поля:

- `id`;
- `study_run_id`;
- `horizon_trading_days`;
- `sample_size`;
- `skipped_count`;
- `median_return_percent nullable`;
- `average_return_percent nullable`;
- `hit_rate_percent nullable`;
- `median_market_relative_percent nullable`;
- `median_sector_relative_percent nullable`;
- `best_horizon_flag`.

Связи:

- many-to-one к `study_runs`.

Уникальные ограничения:

- unique `(study_run_id, horizon_trading_days)`.

Индексы:

- `ix_study_horizon_summary_run_id`;
- `ix_study_horizon_summary_best_horizon`.

Типы:

- percent fields: `Numeric`.

`horizon_trading_days` означает торговые дни. Название намеренно длиннее, чем `horizon_days`, чтобы не смешивать торговые и календарные интервалы.

### 5.17 `reporting_periods`

Назначение: справочник отчетных периодов для future metrics layer.

Ключевые поля:

- `id`;
- `period_type`;
- `period_start`;
- `period_end`;
- `label`.

Уникальные ограничения:

- unique `(period_type, period_start, period_end)`.

Индексы:

- `ix_reporting_periods_type_start`.

### 5.18 `metrics_catalog`

Назначение: справочник метрик.

Ключевые поля:

- `id`;
- `code`;
- `name`;
- `metric_type`;
- `sector_id nullable`;
- `unit`;
- `frequency`;
- `entity_type`;
- `value_type`;
- `description nullable`.

Связи:

- optional many-to-one к `sectors`;
- one-to-many к `metric_observations`.

Уникальные ограничения:

- unique `code`.

Индексы:

- `ix_metrics_catalog_metric_type`;
- `ix_metrics_catalog_sector_id`;
- `ix_metrics_catalog_entity_type`.

Комментарий:

`entity_type` может быть:

- `issuer`;
- `sector`;
- `instrument`;
- `market`.

### 5.19 `metric_observations`

Назначение: значения метрик за отчетные периоды.

Ключевые поля:

- `id`;
- `metric_id`;
- `issuer_id nullable`;
- `sector_id nullable`;
- `instrument_id nullable`;
- `reporting_period_id`;
- `numeric_value nullable`;
- `text_value nullable`;
- `source_id nullable`;
- `published_at nullable`;
- `created_at`.

Связи:

- many-to-one к `metrics_catalog`;
- optional many-to-one к `issuers`;
- optional many-to-one к `sectors`;
- optional many-to-one к `instruments`;
- many-to-one к `reporting_periods`;
- optional many-to-one к `data_sources`.

Уникальные ограничения:

- для MVP можно unique `(metric_id, issuer_id, sector_id, instrument_id, reporting_period_id)`;
- в будущем может понадобиться source-aware uniqueness.

Индексы:

- `ix_metric_observations_metric_period`;
- `ix_metric_observations_issuer_id`;
- `ix_metric_observations_sector_id`;
- `ix_metric_observations_instrument_id`;

Типы:

- `numeric_value`: `Numeric`;
- `text_value`: text.

## 6. Constraints and Indexes

### Unique constraints

Обязательные:

- `instruments`: `(engine, market, board, secid)`;
- `sectors`: `code`;
- `benchmarks`: `code`;
- `data_sources`: `code`;
- `price_candles`: `(instrument_id, interval, begin_at)`;
- `event_types`: `code`;
- `events`: optional `(source_id, source_event_id)` when `source_event_id` is available;
- `event_values`: `(event_id, key)`;
- `study_run_events`: `(study_run_id, event_id)`;
- `study_event_results`: `(study_run_id, event_id, instrument_id, horizon_trading_days)`;
- `study_horizon_summary`: `(study_run_id, horizon_trading_days)`;
- `reporting_periods`: `(period_type, period_start, period_end)`;
- `metrics_catalog`: `code`.

### Foreign keys

Ключевые FK:

- `instruments.issuer_id -> issuers.id`;
- `issuer_sector_history.issuer_id -> issuers.id`;
- `issuer_sector_history.sector_id -> sectors.id`;
- `benchmarks.instrument_id -> instruments.id`;
- `benchmarks.sector_id -> sectors.id`;
- `price_candles.instrument_id -> instruments.id`;
- `price_candles.source_id -> data_sources.id`;
- `price_candles.ingestion_run_id -> ingestion_runs.id`;
- `events.event_type_id -> event_types.id`;
- `events.source_id -> data_sources.id`;
- `event_values.event_id -> events.id`;
- `study_runs.main_instrument_id -> instruments.id`;
- `study_runs.sector_id -> sectors.id`;
- `study_runs.market_benchmark_id -> benchmarks.id`;
- `study_runs.sector_benchmark_id -> benchmarks.id`;
- `study_event_results.study_run_id -> study_runs.id`;
- `study_event_results.event_id -> events.id`;
- `study_event_results.instrument_id -> instruments.id`.

### Индексы для candles

Основной индекс:

- `(instrument_id, interval, begin_at)`.

Дополнительные:

- `(instrument_id, interval, trading_date)`;
- `(begin_at)`;
- `(trading_date)`;
- `(interval, begin_at)`;
- `(instrument_id, begin_at)`.

Эти индексы нужны для:

- поиска event candle `>= event_date`;
- поиска horizon candle через N торговых свечей;
- выборки диапазона дат;
- дедупликации imports.

### Индексы для events

Основной:

- `(event_type_id, event_date)`.

Дополнительные:

- `(event_date)`;
- `(direction)`;
- `(source_id)`.

### Индексы для study results

Основные:

- `(study_run_id, horizon_trading_days)`;
- `(study_run_id, event_id)`;
- `(instrument_id, horizon_trading_days)`;
- `(status)`.

Они нужны для быстрой сборки:

- event-level table;
- horizon summary;
- benchmark comparison;
- debug skipped events.

## 7. Как мигрировать без сноса БД

Стратегия:

1. Не удалять старые таблицы сразу.

   `tickers`, `ticker_latest_prices`, `watchlist_items`, `alerts`, `alert_events`, `key_rate_decisions` должны продолжать работать.

2. Добавлять новые таблицы параллельно.

   Сначала reference layer, потом market data, потом event/study layer.

3. Постепенно связать `tickers` с `instruments`.

   Возможные варианты:

   - добавить `instrument_id` в `tickers`;
   - или постепенно заменить `tickers` на `instruments` в сервисах;
   - не делать это одним большим PR.

   Рекомендуемая последовательность:

   - сначала создать `instruments`;
   - сделать backfill из текущих `tickers`;
   - добавить совместимость в read path;
   - постепенно перевести market/watchlist/alerts/analyzer services на `instrument_id`;
   - только после стабилизации думать об удалении legacy tables.

4. Watchlist/alerts временно оставить на текущих таблицах.

   Их можно перевести на `instrument_id` позже, когда reference layer стабилен.

5. Key Rate Analyzer сначала оставить рабочим.

   Затем:

   - загрузить daily candles в `price_candles`;
   - перенести key rate decisions в generic `events/event_values`;
   - добавить study layer;
   - переключить analyzer на новую модель.

6. Делать миграции маленькими шагами.

   Примерный порядок:

   - create reference tables;
   - backfill instruments from tickers;
   - create price_candles;
   - import candles;
   - create event tables;
   - backfill key rate events;
   - create study tables;
   - switch analyzer read path.

7. После каждого шага прогонять:

   - `alembic upgrade head`;
   - backend tests;
   - smoke API check;
   - live demo critical flows.

## 8. Что входит в v2, а что позже

### v2 must-have

- `issuers`;
- `instruments`;
- `sectors`;
- `issuer_sector_history`;
- `benchmarks`;
- `data_sources`;
- `price_candles`;
- `event_types`;
- `events`;
- `event_values`;
- `study_runs`;
- `study_run_events`;
- `study_event_results`;
- `study_horizon_summary`;
- Key Rate Analyzer v2 через новую модель.

### v2 optional

- минимальный `metrics_catalog`;
- минимальные `reporting_periods`;
- несколько ручных `metric_observations` для проверки будущего направления.

Не стоит в v2 сразу массово наполнять sector/company metrics, если нет стабильного источника данных.

### v2.5 / v3

- sector-specific operational metrics;
- company financial metrics;
- richer metrics analysis;
- сохраненные пользовательские hypotheses;
- portfolio analytics;
- второй/третий event analyzer.

## 9. Риски

### Overengineering

Риск: спроектировать слишком большую БД и надолго застрять без видимого product progress.

Как снижать:

- сначала reference + daily candles + key rate event-study;
- metrics layer оставить минимальным;
- не делать универсальную платформу для всего сразу.

### Слишком ранние sector metrics

Риск: начать собирать операционные метрики банков, нефтяников, металлургов до того, как готов event-study foundation.

Как снижать:

- сначала сектор как benchmark/classification;
- потом sector-specific metrics.

### Отсутствие source provenance

Риск: через месяц будет непонятно, откуда пришли данные и можно ли им доверять.

Как снижать:

- ввести `data_sources`;
- использовать `source_id`;
- хранить ingestion metadata.

### Дубли свечей

Риск: chunking/pagination/import повторно загрузит одни и те же candles.

Как снижать:

- unique `(instrument_id, interval, begin_at)`;
- importer через upsert;
- тесты на duplicate rows.

### Смешивание issuer/instrument

Риск: SBER/SBERP, sector metrics и candles начнут конфликтовать.

Как снижать:

- issuer для компании;
- instrument для торгуемой бумаги;
- candles только на instrument;
- company metrics обычно на issuer.

### Большой breaking refactor live demo

Риск: сломать работающий demo ради v2.

Как снижать:

- не удалять старые endpoints;
- добавлять новые таблицы параллельно;
- переключать analyzer постепенно;
- держать smoke tests.

## 10. Рекомендованный порядок внедрения

### Phase 1: Reference Layer

Цель:

- создать фундамент справочников.

Задачи:

- добавить `issuers`;
- добавить `instruments`;
- добавить `sectors`;
- добавить `issuer_sector_history`;
- добавить `benchmarks`;
- добавить `data_sources`;
- backfill instruments из текущих `tickers`.

Результат:

- можно определить, какая акция к какой компании и сектору относится.

### Phase 2: Price Candles

Цель:

- перестать зависеть от live MOEX calls внутри analyzer.

Задачи:

- добавить `price_candles`;
- добавить `ingestion_runs`;
- сделать daily candles importer;
- deduplicate/upsert по `(instrument_id, interval, begin_at)`;
- покрыть importer тестами.

Результат:

- event-study может читать candles из БД.

### Phase 3: Event / Study Layer

Цель:

- сделать generic event-study foundation.

Задачи:

- добавить `event_types`;
- добавить `events`;
- добавить `event_values`;
- добавить `study_runs`;
- добавить `study_run_events`;
- добавить `study_event_results`;
- добавить `study_horizon_summary`.

Результат:

- Key Rate Analyzer становится частным случаем общего event-study engine.

### Phase 4: Key Rate Analyzer Migration

Цель:

- перевести текущий analyzer на новую модель без изменения пользовательской идеи.

Задачи:

- импортировать `key_rate_decisions` в `events/event_values`;
- читать candles из `price_candles`;
- записывать результаты в `study_*`;
- сохранить текущий endpoint или добавить v2 endpoint рядом.

Результат:

- analyzer становится воспроизводимым и расширяемым.

### Phase 5: Sector Benchmark Output

Цель:

- добавить сравнение акции с сектором и рынком.

Задачи:

- определить sector benchmark для instrument;
- определить market benchmark;
- считать:
  - absolute return;
  - relative to market;
  - relative to sector;
- расширить API response и frontend result panel.

Результат:

- FinLab начинает отвечать не только "акция выросла/упала", но и "лучше/хуже сектора и рынка".

### Phase 6: Future Metrics Layer

Цель:

- подготовить основу для операционных и финансовых метрик.

Задачи:

- добавить `reporting_periods`;
- добавить `metrics_catalog`;
- добавить `metric_observations`;
- начать с 3-5 ручных/curated metrics, без массового импорта.

Результат:

- появляется база для будущего sector/company analytics.

## 11. Зафиксированные решения и ручная проверка

В этой версии спецификации зафиксированы следующие архитектурные defaults:

1. Секторная принадлежность: `issuer_sector_history`.

   Сектор относится к компании/эмитенту. Instrument-level override можно добавить позже отдельной таблицей, если появятся реальные исключения.

2. Candles date/time: `begin_at` + `trading_date`.

   `begin_at` хранится как timezone-aware `DateTime`, `trading_date` — как `Date`. Для daily candles `begin_at` нормализуется к дате/началу торгового дня, а `trading_date` используется для поиска торговых горизонтов.

3. Horizon naming: `horizon_trading_days`.

   Горизонты в study layer считаются в торговых днях, а не календарных.

4. Market benchmark: индекс как instrument.

   Market index вроде IMOEX хранится как `instrument` с `asset_type = index`, а `benchmarks` ссылается на этот instrument. Это отделяет индекс IMOEX от акции `MOEX`.

5. Study results persistent.

   `study_runs`, `study_event_results` и `study_horizon_summary` должны сохраняться, чтобы анализ был воспроизводимым.

6. Legacy `tickers`.

   Текущие `tickers` временно остаются. Сначала создаются `instruments`, затем делается backfill, затем сервисы постепенно переводятся на новую модель.

Перед миграциями все еще нужно вручную проверить:

- доступен ли надежный источник candles для IMOEX или другого market benchmark;
- какую timezone использовать для нормализации `begin_at`;
- какие source-specific external ids доступны для событий;
- какие минимальные sectors/benchmarks нужны для первого v2 demo;
- стоит ли включать future metrics layer в первую пачку миграций или оставить только в спецификации.

## 12. Analytics DB Core Implementation Notes

This section fixes the target v2 analytics DB core implemented after the initial reference layer.
It is intentionally additive: legacy `tickers`, `ticker_latest_prices`, `watchlist_items`,
`alerts`, `alert_events` and `key_rate_decisions` remain untouched until separate migration
tasks move read/write paths.

### 12.1 Reference Layer Boundary

The reference layer remains:

- `issuers`;
- `instruments`;
- `sectors`;
- `issuer_sector_history`;
- `benchmarks`;
- `data_sources`.

Important benchmark rule:

- `MOEX` is the stock/instrument of Moscow Exchange and must not be treated as the market benchmark.
- A market benchmark must point to a real index instrument, for example `IMOEX`, only when the project has reliable instrument metadata and candle support for it.
- If a market index is not available yet, `benchmarks.instrument_id` stays nullable/unavailable. Do not silently substitute the `MOEX` stock as the market benchmark.

### 12.2 Market Data Layer

The v2 market data core contains:

- `trading_calendar` for market trading days and session metadata;
- `ingestion_runs` for import/load provenance;
- `price_candles` for persisted OHLCV candles.

`price_candles` uses:

- `begin_at` as timezone-aware DateTime;
- `trading_date` as Date for event-study horizon lookup;
- unique `(instrument_id, interval, begin_at)`;
- index `(instrument_id, interval, trading_date)`;
- nullable `source_id` and nullable `ingestion_run_id`.

`latest_prices` is not part of the current analytics-core migration. It can be added later as a v2 replacement for legacy `ticker_latest_prices` if the live/demo read path is migrated.

### 12.3 Event Layer

The generic event layer contains:

- `event_types`;
- `events`;
- `event_values`;
- `event_targets`.

`events.source_event_id` is nullable and indexed. If a source provides stable unique ids, future importers should use it for deduplication. Exact partial uniqueness for `(source_id, source_event_id)` can be added later in a Postgres-specific migration once importer behavior is stable.

`event_targets` allows an event to target:

- market;
- sector;
- issuer;
- instrument;
- benchmark.

Nullable target columns make strict database-level uniqueness awkward, so exact target uniqueness can be enforced in business/import validation first.

### 12.4 Benchmark And Sector Composition

`benchmark_constituents` supports synthetic sector baskets and benchmark composition.

Sector return can be calculated by:

- a real sector benchmark instrument, if available;
- a synthetic equal-weight basket based on sector instruments;
- a median sector basket based on sector instruments.

This table is composition/provenance foundation only. It does not calculate returns by itself.

### 12.5 Study Layer

The v2 study layer contains:

- `study_runs`;
- `study_run_events`;
- `study_event_results`;
- `study_benchmark_results`;
- `study_comparisons`;
- `study_horizon_summary`;
- `study_skipped_events`.

Study runs store:

- `methodology_version`;
- `params_json`;
- optional `data_version`;
- optional `data_cutoff_at`;
- status and error fields.

Per-event outputs are split deliberately:

- `study_event_results` stores target instrument returns;
- `study_benchmark_results` stores benchmark or synthetic basket returns;
- `study_comparisons` stores relative results such as `relative_to_market` and `relative_to_sector`;
- `study_skipped_events` stores explicit audit/debug reasons for missing data or invalid event/candle combinations.

All horizons are trading-day horizons and should use `horizon_trading_days`, not calendar-day naming.

### 12.6 Future Metrics Layer

`reporting_periods`, `metrics_catalog` and `metric_observations` stay future-ready only. They are not part of the current analytics DB core migration because stable company/sector fundamental data sources are not ready yet.

### 12.7 Migration Strategy

The current implementation creates the analytics core in parallel with the legacy product layer. It does not:

- switch the legacy Key Rate Impact Analyzer to the new tables;
- delete legacy tables;
- change watchlist, alerts or demo session behavior;
- add frontend UI;
- add auth.

The recommended next steps are:

1. import/persist daily candles into `price_candles`;
2. backfill `key_rate_decisions` into generic `events` and `event_values`;
3. implement a v2 event-study service that reads from `price_candles`, `events` and `study_*`;
4. add sector/market comparison only after proper benchmark/index support is available.

## 13. Market Data Ingestion Strategy

Market data ingestion is intentionally separated from migrations and reference seed.

Rules:

- migrations create only database structure;
- reference seed creates only reference data such as sources, sectors, instruments and benchmark placeholders;
- candles are loaded only by an explicit importer command;
- candles are not hardcoded;
- candles are not loaded through Alembic migrations;
- candles are not loaded through reference seed;
- the project does not automatically import the full market history.

Phase 2.1 supports only:

- daily candles;
- interval `1d`;
- explicit `secid`;
- explicit date range;
- manual CLI run;
- upsert into `price_candles` by `(instrument_id, interval, begin_at)`;
- ingestion audit through `ingestion_runs`.

Example:

```bash
python -m app.modules.market_data.import_candles --secid SBER --from 2024-01-01 --to 2024-02-01
```

Repeated runs for the same instrument/date window must not create duplicate candles. Existing OHLCV rows may be updated with the newest imported values and the latest `ingestion_run_id`.

The importer writes:

- `instrument_id`;
- `interval = 1d`;
- `begin_at`;
- `trading_date`;
- `open`, `high`, `low`, `close`;
- `volume`;
- `value`, when MOEX provides it;
- `source_id = data_sources.moex`, if available;
- `ingestion_run_id`.

Out of scope for Phase 2.1:

- intraday candles;
- full-market historical import;
- automatic background import;
- event-window importer;
- sector comparison;
- switching the legacy Key Rate Impact Analyzer to `price_candles`;
- importing `key_rate_decisions` into the generic `events` table.

## 14. Key Rate Events Migration Strategy

Phase 2.2 backfills the legacy `key_rate_decisions` table into the generic v2 events layer without switching the live analyzer yet.

The legacy table remains the source for the current Key Rate Impact Analyzer MVP. The v2 import is a parallel analytics foundation only:

- no frontend changes;
- no API contract changes;
- no analyzer behavior changes;
- no deletion of `key_rate_decisions`;
- no event-study engine switch yet.

### 14.1 Event Type

Key rate decisions are represented as:

- `event_types.code = key_rate_decision`;
- `event_types.name = Key rate decision`;
- `event_types.default_source_id = data_sources.cbr`, when available.

If `data_sources.cbr` does not exist, the importer may fall back to `manual_seed` or leave `source_id` nullable. This keeps local MVP environments usable while preserving provenance when reference seed has been run.

### 14.2 Event Mapping

Each legacy `key_rate_decisions` row maps to one `events` row:

- `event_date = key_rate_decisions.decision_date`;
- `event_datetime = publication_datetime_msk`, when available;
- `source_event_id = key_rate_decision:{decision_date}`;
- `direction = hike | cut | hold | unknown`;
- `importance = high`;
- `source_id = cbr/manual_seed/null`, depending on available reference data.

Direction is derived from `rate_before` and `rate_after` first:

- `rate_after > rate_before` -> `hike`;
- `rate_after < rate_before` -> `cut`;
- `rate_after == rate_before` -> `hold`.

If rates are incomplete, the importer may fall back to the legacy direction values `rate_hike`, `rate_cut` and `rate_hold`. If neither source is sufficient, direction should be `unknown`.

### 14.3 Event Values

Key rate numeric fields are stored in `event_values`:

- `key_rate` from `rate_after`, unit `percent`;
- `previous_key_rate` from `rate_before`, unit `percent`;
- `change_bps` from `change_bps` or calculated as `(rate_after - rate_before) * 100`, unit `bps`.

Values are upserted by `(event_id, key)`. Re-running the importer must update values instead of creating duplicates.

### 14.4 Event Target

Key rate decisions affect the broad market in this MVP layer. Each imported event gets an `event_targets` row:

- `target_type = market`;
- `instrument_id = null`;
- `issuer_id = null`;
- `sector_id = null`;
- `benchmark_id = null`.

Specific instrument, sector or benchmark targets can be added later if a richer macro event taxonomy needs them.

### 14.5 Idempotency And Cutover

The importer must be idempotent:

- no duplicate `event_types` for `key_rate_decision`;
- no duplicate `events` for the same legacy decision date/source id;
- no duplicate `event_values` for the same `(event_id, key)`;
- no duplicate market `event_targets` for the same event.

Recommended cutover sequence:

1. keep importing legacy `key_rate_decisions` into v2 `events`;
2. validate row counts and duplicate checks;
3. implement a v2 event-study service that reads `events`, `price_candles` and `study_*`;
4. compare v1 analyzer output with v2 output;
5. only then consider switching the API/UI to the v2 engine.

## 15. Event Study Engine v1 Methodology

Phase 2.3 introduces the first working analytics calculation on top of the v2 database layer.

The engine reads:

- events from v2 `events`;
- daily prices from v2 `price_candles`;
- one target instrument from v2 `instruments`.

The engine writes:

- one `study_runs` row per real run;
- `study_run_events`;
- `study_event_results`;
- `study_horizon_summary`;
- `study_skipped_events`, when an event or horizon cannot be calculated.

Current v1 scope:

- one selected instrument by `secid`;
- one selected `event_type.code`, for example `key_rate_decision`;
- daily candles only, `interval = 1d`;
- absolute instrument return only;
- no market benchmark comparison;
- no sector comparison;
- no frontend;
- no API endpoint;
- no switch of the legacy Key Rate Impact Analyzer.

### 15.1 Event Candle Selection

For each event:

1. use `events.event_date` as the anchor;
2. find the first `price_candles` row for the target instrument where:
   - `interval = 1d`;
   - `trading_date >= events.event_date`;
3. use this candle as the event candle.

This means that if an event date is a weekend or non-trading day, the engine uses the nearest following available trading candle from persisted data.

### 15.2 Horizon Candle Selection

For each requested horizon `N`:

1. start from the event candle position inside the instrument's sorted daily candles;
2. select the candle at `event_index + N`;
3. horizons are trading-day offsets based on available candles, not calendar-day offsets.

The field name is `horizon_trading_days` to avoid ambiguity.

### 15.3 Return Formula

For each successful event/horizon pair:

```text
return_percent = (horizon_close - event_close) / event_close * 100
```

All calculations should use `Decimal`/`Numeric`-friendly arithmetic. Missing data must not be converted to fake zero returns.

### 15.4 Skip Rules

The engine skips data explicitly:

- `no_event_candle` when no candle exists on or after the event date;
- `invalid_event_price` when event close is missing or not positive;
- `no_horizon_candles` when the requested horizon candle does not exist;
- `invalid_horizon_price` when the horizon close is missing;
- `no_events_found` when the selected event type/date range has no events.

If an event has at least one successful horizon, `study_run_events.status = success`. If all requested horizons are skipped, `study_run_events.status = skipped` and a `study_skipped_events` row is written.

### 15.5 Study Run Metadata

Each real run creates a new `study_runs` row. Event-study runs are not idempotent by default because each run represents a specific research calculation over a specific data cut.

Required metadata:

- `study_type = event_study`;
- `event_type_id`;
- `target_type = instrument`;
- `target_instrument_id`;
- `params_json`;
- `methodology_version = event_study_v1`;
- `data_cutoff_at = current UTC datetime`;
- `status = running | success | failed`;
- `completed_at` when finished.

Dry-run mode may calculate the same result object but should roll back DB writes.

### 15.6 Horizon Summary

`study_horizon_summary` aggregates only successful `study_event_results`.

For each horizon:

- `sample_size` is the number of successful event/horizon results;
- `skipped_count` is total events minus successful results for that horizon;
- `positive_count`, `negative_count`, `neutral_count` are based on `return_percent`;
- `average_return_percent` and `median_return_percent` ignore skipped/null rows;
- `hit_rate_percent` is positive returns divided by sample size;
- relative-return fields remain `null` in v1.

`best_horizon_flag` may be set for the horizon with the highest average return when at least one horizon has usable data.

## 16. Key Rate Analyzer v2 Cutover Strategy

Phase 2.4 adds a backend-level v2 Key Rate Analyzer orchestration flow. The legacy analyzer remains available and unchanged.

The v2 flow is an orchestrator over:

- reference `instruments`;
- v2 `events` with `event_types.code = key_rate_decision`;
- v2 `price_candles` with `interval = 1d`;
- the v2 event-study engine;
- persisted `study_*` results.

This is an on-demand analysis flow, not an application startup import, background job, scheduled updater or full-market data loader.

### 16.1 Request Flow

The backend receives:

- selected `secid`;
- optional `date_from` and `date_to`;
- trading-day horizons;
- `auto_prepare_data`;
- `refresh_candles`.

Then it:

1. resolves the target instrument in the reference layer;
2. checks whether v2 key rate events exist;
3. if events are missing and `auto_prepare_data = true`, runs the existing key rate events importer service;
4. determines the required daily candle date range from request dates or available events;
5. adds a calendar buffer after `date_to` or the last event date for horizon candles;
6. checks whether daily candles exist for the selected instrument;
7. if candles are missing or `refresh_candles = true`, runs the existing daily candles importer only for the requested instrument/date range;
8. runs the v2 event-study engine;
9. returns a structured result with `study_run_id`, horizon summary and data preparation metadata.

### 16.2 Data Preparation Rules

Data preparation is controlled and request-scoped:

- no full-market imports;
- no startup auto-import;
- no scheduler;
- no background worker;
- no watchlist/latest-price usage;
- no intraday/10m chart candle usage.

The v2 analyzer uses only daily close prices from v2 `price_candles` where `interval = 1d`.

If MOEX candle import fails, the request should return a clear backend error. If candles remain incomplete after preparation, the event-study engine should still record skipped events/horizons instead of inventing zero returns.

### 16.3 API Layer

The initial backend endpoint is:

```text
POST /api/v1/hypotheses/key-rate-impact/v2
```

The old endpoint remains:

```text
POST /api/v1/hypotheses/key-rate-impact/analyze
```

The v2 endpoint does not replace the legacy endpoint yet. Frontend cutover is a separate future step.

### 16.4 Current Scope

Included:

- one target instrument;
- key rate decision events;
- daily candle preparation for the requested instrument/date range;
- absolute instrument returns;
- horizon summary;
- persisted study runs and results.

Excluded:

- sector comparison;
- market benchmark/IMOEX comparison;
- inflation, FX or oil event types;
- frontend changes;
- scheduled refresh;
- Docker/deploy changes.

## 17. Sector Comparison v1

Phase 2.5 adds optional sector comparison to the Key Rate Analyzer v2 backend response.

The selected instrument is compared against a limited deterministic peer set from the same sector. This is a peer-based comparison, not a formal sector index.

### 17.1 Sector Resolution

Sector is resolved through:

- selected `instruments` row;
- selected instrument `issuer_id`;
- latest/current `issuer_sector_history` row for that issuer;
- linked `sectors` row.

For v1 the backend uses the latest available issuer-sector mapping. Event-date-aware sector history can be added later if sector membership changes become important for historical studies.

If no mapping exists, the main Key Rate v2 analysis still succeeds and `sector_comparison.status = no_sector_mapping`.

### 17.2 Peer Selection

Peers are selected from instruments whose issuer belongs to the same sector:

- same sector as selected instrument;
- same `asset_type`;
- active instruments only;
- selected instrument excluded;
- deterministic order by `secid`;
- limited by request `sector_peer_limit`.

The default peer limit is intentionally small. This prevents accidental full-sector/full-market imports during an interactive analysis request.

### 17.3 Data Sources

Sector comparison uses only v2 daily candles:

- `price_candles.interval = 1d`;
- daily close prices;
- same event type/date range/horizons as the selected instrument.

It must not use:

- 10m/intraday chart candles;
- latest/watchlist prices;
- saved UI chart data;
- market benchmark/IMOEX data.

### 17.4 Missing Peer Data

If peer daily candles are missing:

- with `auto_prepare_sector_data = false`, the peer is skipped with `missing_daily_candles`;
- with `auto_prepare_sector_data = true`, the backend may import daily candles only for the selected limited peer set and required date range;
- failed peer imports skip that peer and do not fail the main selected-instrument analysis.

The response tracks:

- peers found before limit;
- peers used after data checks;
- skipped peers and reasons;
- peer candle importer run count;
- peer rows loaded.

### 17.5 Calculation

For each usable peer, v1 applies the same event-study methodology:

- event candle = first daily candle with `trading_date >= event.event_date`;
- horizon candle = Nth trading candle after the event candle;
- return = `(horizon_close - event_close) / event_close * 100`.

For each horizon the response includes:

- selected instrument average return;
- peer/sector average return;
- peer/sector median return;
- excess return versus the sector peer average;
- selected rank among selected instrument plus usable peers;
- peer count and sector hit rate.

### 17.6 Current Scope

Included:

- optional response field `sector_comparison`;
- peer-based average/median comparison;
- bounded on-demand peer candle preparation.

Excluded:

- formal sector index construction;
- persisted `study_comparisons` cutover;
- market benchmark/IMOEX;
- frontend cutover;
- scheduled sector data refresh;
- full-market import.
