const PRIMARY_HORIZONS = new Set([1, 3, 10]);

export function HypothesisResultPanel({ result, isLoading }) {
  if (isLoading && !result) {
    return (
      <div className="hypothesisResult">
        <div className="emptyState hypothesisPlaceholder">
          <strong>Анализируем исторические решения ЦБ и свечи MOEX...</strong>
          <p>
            Сравниваем похожие решения по ключевой ставке с движением выбранной
            акции на заданных горизонтах.
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="hypothesisResult">
        <div className="emptyState hypothesisPlaceholder">
          <strong>
            Выберите акцию и сценарий ставки, чтобы проверить историческую
            реакцию.
          </strong>
          <p>
            Результат покажет краткий вывод, уверенность, выраженный горизонт
            и реакцию по выбранным периодам.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="hypothesisResult">
      <SummaryCard summary={result.summary} />
      <div className="resultPairGrid">
        <ConfidenceCard confidence={result.confidence} />
        <BestHorizonCard bestHorizon={result.best_horizon} />
      </div>
      {!result.benchmark_ticker && (
        <p className="benchmarkInlineNote">
          Бенчмарк не выбран — показана абсолютная реакция акции.
        </p>
      )}
      <HorizonSummaryTable items={result.horizon_summary || []} />
      <BenchmarkSummary result={result} />
      <DataQualityDetails
        skippedSummary={result.skipped_summary}
        summary={result.summary}
      />
      <Limitations limitations={result.limitations || []} />
      <EventDetails events={result.event_results || []} />
    </div>
  );
}

function SummaryCard({ summary }) {
  const title = buildSummaryTitle(summary);

  return (
    <section className="assessmentCard">
      <span className={`assessmentBadge ${summary?.result_type || ""}`}>
        {formatResultType(summary?.result_type)}
      </span>
      <h3>{title}</h3>
      <p>{summary?.short_conclusion}</p>
      <div className="summaryStats">
        <span>
          {summary?.events_used || 0} событий проанализировано
        </span>
        {(summary?.events_skipped ?? 0) > 0 && (
          <span>Пропущено: {summary.events_skipped}</span>
        )}
      </div>
      <p className="resultHint">
        Историческая реакция не является прогнозом.
      </p>
    </section>
  );
}

function ConfidenceCard({ confidence }) {
  return (
    <section className="resultBlock compactResultBlock">
      <div className="resultBlockHeader">
        <h3>Уверенность анализа</h3>
      </div>
      <strong className="insightValue">
        {confidence?.label || "Не рассчитана"}
      </strong>
      <ul className="limitationList">
        {(confidence?.reasons || []).slice(0, 3).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </section>
  );
}

function BestHorizonCard({ bestHorizon }) {
  if (!bestHorizon) {
    return (
      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Выраженный горизонт не найден</h3>
        </div>
        <p className="resultHint">
          Для выбранного сценария недостаточно событий с рыночными данными.
        </p>
      </section>
    );
  }

  return (
    <section className="resultBlock compactResultBlock">
      <div className="resultBlockHeader">
        <h3>Самый выраженный горизонт</h3>
      </div>
      <strong className="insightValue">{bestHorizon.horizon_label}</strong>
      <div className="resultMetricsGrid compact">
        <Metric
          label="Средняя реакция"
          value={formatPercent(bestHorizon.average_return_percent)}
          tone={getTone(bestHorizon.average_return_percent)}
        />
        <Metric
          label="Медиана"
          value={formatPercent(bestHorizon.median_return_percent)}
          tone={getTone(bestHorizon.median_return_percent)}
        />
        <Metric label="Событий / покрытие" value={bestHorizon.events_with_data} />
      </div>
      <p className="resultHint">
        {bestHorizon.typical_effect_label || bestHorizon.typical_effect}.
        {bestHorizon.reason ? ` ${bestHorizon.reason}` : ""}
      </p>
    </section>
  );
}

function HorizonSummaryTable({ items }) {
  const visibleItems = items.filter((item) => PRIMARY_HORIZONS.has(item.horizon_days));

  return (
    <section className="resultBlock">
      <div className="resultBlockHeader">
        <h3>Реакция по горизонтам</h3>
      </div>
      {visibleItems.length === 0 ? (
        <p className="resultHint">Нет данных для таблицы горизонтов.</p>
      ) : (
        <div className="tableWrapper compactTable">
          <table>
            <thead>
              <tr>
                <th>Горизонт</th>
                <th>Средняя реакция</th>
                <th>Медиана</th>
                <th>События</th>
                <th>Интерпретация</th>
                <th>Покрытие</th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.map((item) => (
                <tr
                  className={item.events_with_data < 3 ? "mutedDataRow" : undefined}
                  key={item.horizon_days}
                >
                  <td>{item.horizon_label || `${item.horizon_days} дн.`}</td>
                  <td className={getTone(item.average_return_percent)}>
                    {formatPercent(item.average_return_percent)}
                  </td>
                  <td className={getTone(item.median_return_percent)}>
                    {formatPercent(item.median_return_percent)}
                  </td>
                  <td>
                    {formatEventCounts(item)}
                  </td>
                  <td>
                    {formatEffect(item)}
                  </td>
                  <td>
                    {item.events_with_data} / {item.events_total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function BenchmarkSummary({ result }) {
  const benchmarkItems = result.benchmark_summary || [];

  if (!result.benchmark_ticker) {
    return null;
  }

  return (
    <section className="resultBlock secondaryResultBlock">
      <div className="resultBlockHeader">
        <h3>Сравнение с бенчмарком</h3>
      </div>
      {result.benchmark_ticker && benchmarkItems.length > 0 ? (
        <div className="tableWrapper compactTable">
          <table>
            <thead>
              <tr>
                <th>Горизонт</th>
                <th>Бенчмарк</th>
                <th>Относительно акции</th>
                <th>Лучше / хуже</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkItems.map((item) => (
                <tr key={item.horizon_days}>
                  <td>{item.horizon_days} дн.</td>
                  <td className={getTone(item.average_benchmark_return_percent)}>
                    {formatPercent(item.average_benchmark_return_percent)}
                  </td>
                  <td className={getTone(item.average_relative_return_percent)}>
                    {formatPercent(item.average_relative_return_percent)}
                    <span className="tableSubtext">
                      медиана {formatPercent(item.median_relative_return_percent)}
                    </span>
                  </td>
                  <td>
                    {item.outperformed_count} / {item.underperformed_count}
                    <span className="tableSubtext">
                      лучше: {formatPercent(item.outperformed_share_percent)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="resultHint">Сравнение с бенчмарком недоступно.</p>
      )}
    </section>
  );
}

function DataQualityDetails({ skippedSummary, summary }) {
  const reasons = skippedSummary?.reasons || [];
  const analyzed = summary?.events_used || 0;
  const total = summary?.events_total || 0;
  const skipped = skippedSummary?.skipped_total ?? summary?.events_skipped ?? 0;

  return (
    <section className="resultBlock secondaryResultBlock">
      <details className="eventDetails">
        <summary>Качество данных</summary>
        <div className="detailsBody">
          <p className="resultHint">
            Проанализировано: {analyzed} из {total} событий. Пропущено: {skipped}.
          </p>
          {reasons.length > 0 && (
            <ul className="limitationList">
              {reasons.map((item) => (
                <li key={item.reason}>
                  {formatSkipReason(item.reason)}: {item.count}
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </section>
  );
}

function Limitations({ limitations }) {
  return (
    <section className="resultBlock secondaryResultBlock">
      <details className="eventDetails">
        <summary>Ограничения анализа</summary>
        <ul className="limitationList detailsList">
          {buildLimitations(limitations).map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function EventDetails({ events }) {
  if (events.length === 0) {
    return null;
  }

  return (
    <section className="resultBlock secondaryResultBlock">
      <details className="eventDetails">
        <summary>Исторические события</summary>
        <div className="eventDetailsList">
          {events.map((event) => (
            <article key={`${event.decision_date}-${event.direction}`}>
              <strong>{event.decision_date}</strong>
              <p>
                {formatEventDirection(event.direction)}
                {event.change_bps !== null && event.change_bps !== undefined
                  ? ` / ${event.change_bps} б.п.`
                  : ""}
                {formatEventStatus(event.status)
                  ? ` / ${formatEventStatus(event.status)}`
                  : ""}
              </p>
              <p>
                {event.rate_before ?? "-"} → {event.rate_after ?? "-"}
                {event.skip_reason ? ` / ${formatSkipReason(event.skip_reason)}` : ""}
              </p>
              <div>
                {(event.horizons || []).map((horizon) => (
                  <span key={horizon.horizon_days}>
                    {horizon.horizon_days}д:{" "}
                    {formatPercent(horizon.stock_return_percent)}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </details>
    </section>
  );
}

function Metric({ label, value, tone }) {
  const className = tone ? `resultMetric ${tone}` : "resultMetric";

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}

function buildSummaryTitle(summary) {
  if (!summary) {
    return "Историческая реакция";
  }

  return `${summary.company_name || summary.main_ticker} после ${formatDirectionForTitle(
    summary.direction,
    summary.direction_label,
  )}`;
}

function formatDirectionForTitle(direction, fallbackLabel) {
  const labels = {
    rate_cut: "снижения ключевой ставки",
    rate_hike: "повышения ключевой ставки",
    rate_hold: "сохранения ключевой ставки",
  };

  return (
    labels[direction] ||
    fallbackLabel?.toLocaleLowerCase("ru-RU") ||
    "решения по ключевой ставке"
  );
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return value;
  }

  const prefix = numberValue > 0 ? "+" : "";

  return `${prefix}${new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numberValue)}%`;
}

function formatResultType(value) {
  const labels = {
    positive: "Чаще рост",
    negative: "Чаще снижение",
    neutral: "Нейтрально",
    mixed: "Смешанная реакция",
    insufficient_data: "Недостаточно данных",
  };

  return labels[value] || "исторический анализ";
}

function formatEventCounts(item) {
  return `${item.positive_count} рост / ${item.negative_count} падение / ${item.neutral_count} нейтр.`;
}

function formatEffect(item) {
  if (
    item.events_with_data < 3 ||
    item.typical_effect === "insufficient_data" ||
    item.typical_direction === "insufficient_data"
  ) {
    return "отдельные наблюдения";
  }

  const effect = formatEffectLabel(item.typical_effect_label || item.typical_effect);
  const direction = formatDirectionLabel(
    item.typical_direction_label || item.typical_direction,
  );

  if (!effect && !direction) {
    return "-";
  }

  if (!effect || effect === direction) {
    return direction || effect;
  }

  if (!direction || direction === "нейтрально" || direction === "neutral") {
    return effect;
  }

  return `${effect}, ${direction}`;
}

function formatEffectLabel(value) {
  const labels = {
    weak_positive: "слабый рост",
    weak_negative: "слабое падение",
    strong_positive: "заметный рост",
    strong_negative: "заметное падение",
    mixed: "смешанно",
    neutral: "шум",
    noise: "шум",
    insufficient_data: "отдельные наблюдения",
  };

  return labels[value] || value;
}

function formatDirectionLabel(value) {
  const labels = {
    positive: "рост",
    negative: "падение",
    neutral: "нейтр.",
    mixed: "смешанно",
    insufficient_data: "отдельные наблюдения",
  };

  return labels[value] || value;
}

function buildLimitations(limitations) {
  const defaults = [
    "Историческая реакция не является прогнозом.",
    "Корреляция не доказывает причинно-следственную связь.",
    "Дивиденды, корпоративные события и новости могут влиять на результат.",
    "Часть событий может быть пропущена из-за отсутствия рыночных данных.",
  ];

  if (!limitations?.length) {
    return defaults;
  }

  return [...new Set([...defaults, ...limitations.map(formatLimitation)])].slice(0, 4);
}

function formatLimitation(value) {
  const lowerValue = String(value || "").toLowerCase();

  if (lowerValue.includes("forecast")) {
    return "Историческая реакция не является прогнозом.";
  }

  if (lowerValue.includes("causality") || lowerValue.includes("correlation")) {
    return "Корреляция не доказывает причинно-следственную связь.";
  }

  if (lowerValue.includes("corporate")) {
    return "Дивиденды, корпоративные события и новости могут влиять на результат.";
  }

  if (lowerValue.includes("missing") || lowerValue.includes("candle")) {
    return "Часть событий может быть пропущена из-за отсутствия рыночных данных.";
  }

  return value;
}

function formatEventDirection(value) {
  const labels = {
    rate_cut: "Снижение ставки",
    rate_hike: "Повышение ставки",
    rate_hold: "Ставка без изменений",
  };

  return labels[value] || value || "-";
}

function formatEventStatus(value) {
  const labels = {
    ok: "",
    market_disruption: "рыночный шок",
    extraordinary: "нестандартное событие",
  };

  return labels[value] ?? value ?? "";
}

function formatSkipReason(value) {
  const labels = {
    baseline_not_found: "нет базовой свечи",
    event_trading_day_not_found: "нет торгового дня события",
    horizon_candle_not_found: "нет свечи горизонта",
    some_horizons_missing: "часть горизонтов недоступна",
    invalid_decision_date: "некорректная дата решения",
  };

  return labels[value] || value || "-";
}

function getTone(value) {
  const numberValue = Number(value);

  if (Number.isNaN(numberValue) || numberValue === 0) {
    return undefined;
  }

  return numberValue > 0 ? "positive" : "negative";
}
