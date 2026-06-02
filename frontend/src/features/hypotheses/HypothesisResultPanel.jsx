import { formatPrice } from "../../shared/lib/formatters.js";

export function HypothesisResultPanel({ result, isLoading }) {
  if (isLoading && !result) {
    return (
      <div className="hypothesisResult">
        <div className="emptyState">
          <strong>Анализируем гипотезу</strong>
          <p>
            Получаем свечи, проверяем окно события и собираем отчет по выбранным
            параметрам.
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="hypothesisResult">
        <div className="emptyState">
          <strong>Заполните параметры слева и запустите анализ.</strong>
          <p>
            Отчет покажет фундаментальную логику, историческую реакцию цены и
            факторы, за которыми стоит наблюдать.
          </p>
        </div>
      </div>
    );
  }

  const { assessment, historical_validation: historicalValidation } = result;
  const mainResult = historicalValidation?.main_ticker_result;
  const benchmarkResult = historicalValidation?.benchmark_result;
  const relativeResult = historicalValidation?.relative_result;
  const benchmarkTicker = result.hypothesis?.benchmark_ticker;

  return (
    <div className="hypothesisResult">
      <section className="assessmentCard">
        <div>
          <span className={`assessmentBadge ${assessment?.overall_result || ""}`}>
            {formatResultLabel(assessment?.overall_result)}
          </span>
          <h3>Уверенность: {formatResultLabel(assessment?.confidence || "low")}</h3>
          <p>{assessment?.text}</p>
        </div>
      </section>

      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Проверка основного тикера</h3>
        </div>
        <div className="resultMetricsGrid">
          <Metric label="Цена до события" value={formatPrice(mainResult?.price_before)} />
          <Metric label="Цена события" value={formatPrice(mainResult?.price_at_event)} />
          <Metric label="Цена после" value={formatPrice(mainResult?.price_after)} />
          <Metric
            label="Доходность после"
            value={formatPercent(mainResult?.return_after_percent)}
            tone={getTone(mainResult?.return_after_percent)}
          />
          <Metric
            label="Макс. просадка"
            value={formatPercent(mainResult?.max_drawdown_after_percent)}
            tone="negative"
          />
          <Metric
            label="Макс. рост"
            value={formatPercent(mainResult?.max_runup_after_percent)}
            tone="positive"
          />
          <Metric
            label="Волатильность"
            value={formatPercent(mainResult?.volatility_after_percent)}
          />
        </div>
      </section>

      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Сравнение с бенчмарком</h3>
        </div>

        {benchmarkResult?.status === "ok" && relativeResult ? (
          <div className="resultMetricsGrid compact">
            <Metric
              label="Доходность бенчмарка"
              value={formatPercent(relativeResult.benchmark_return_after_percent)}
              tone={getTone(relativeResult.benchmark_return_after_percent)}
            />
            <Metric
              label="Относительная доходность"
              value={formatPercent(relativeResult.relative_return_after_percent)}
              tone={getTone(relativeResult.relative_return_after_percent)}
            />
            <Metric
              label="Интерпретация"
              value={formatResultLabel(relativeResult.interpretation)}
            />
          </div>
        ) : (
          <div className="emptyState compact">
            <strong>{getBenchmarkStateTitle({ benchmarkTicker, benchmarkResult })}</strong>
            <p>{getBenchmarkStateText({ benchmarkTicker, benchmarkResult })}</p>
          </div>
        )}
      </section>

      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Механизмы влияния</h3>
        </div>
        <div className="mechanismGrid">
          {(result.blueprint?.mechanisms || []).map((mechanism) => (
            <article className="mechanismCard" key={mechanism.id}>
              <div>
                <strong>{mechanism.name}</strong>
                <span>
                  {formatResultLabel(mechanism.direction)} /{" "}
                  {formatResultLabel(mechanism.importance)}
                </span>
              </div>
              <p>{mechanism.explanation}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="resultBlock argumentColumns">
        <ArgumentList title="Аргументы за" items={result.arguments_for} />
        <ArgumentList title="Аргументы против" items={result.arguments_against} />
      </section>

      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Что отслеживать</h3>
        </div>
        <div className="watchFactorList">
          {(result.watch_factors || []).map((factor) => (
            <article key={factor.id}>
              <strong>{factor.name}</strong>
              <p>{factor.why_it_matters}</p>
              <div>
                <span>Позитивный сигнал: {factor.signal_positive}</span>
                <span>Негативный сигнал: {factor.signal_negative}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Ограничения</h3>
        </div>
        <ul className="limitationList">
          {(result.limitations || []).map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </section>

      <section className="resultBlock">
        <div className="resultBlockHeader">
          <h3>Идеи для наблюдения</h3>
        </div>
        <p className="resultHint">
          Alert'ы не создаются автоматически. Это ориентиры, которые можно позже
          перенести в правила уведомлений.
        </p>
        <div className="suggestedAlertList">
          {(result.suggested_alerts || []).map((alert, index) => (
            <article key={`${alert.id || alert.secid}-${index}`}>
              <strong>{alert.title || alert.secid || "Идея для наблюдения"}</strong>
              <p>{alert.description || alert.reason}</p>
              <span>
                {formatResultLabel(alert.condition || alert.condition_hint || "watch")} /{" "}
                {alert.target_price
                  ? formatPrice(alert.target_price)
                  : "уровень не рассчитан"}
              </span>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone }) {
  const className = tone ? `resultMetric ${tone}` : "resultMetric";

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ArgumentList({ title, items = [] }) {
  return (
    <div>
      <h3>{title}</h3>
      <div className="argumentList">
        {items.map((item) => (
          <article key={`${item.type}-${item.message}`}>
            <span>{formatResultLabel(item.type)}</span>
            <p>{item.message}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function getBenchmarkStateTitle({ benchmarkTicker, benchmarkResult }) {
  if (!benchmarkTicker) {
    return "Сравнение с бенчмарком отключено.";
  }

  if (benchmarkResult?.status === "failed") {
    return "Сравнение с бенчмарком недоступно.";
  }

  return "Нет данных для сравнения.";
}

function getBenchmarkStateText({ benchmarkTicker, benchmarkResult }) {
  if (!benchmarkTicker) {
    return "Итог основан только на основном тикере.";
  }

  if (benchmarkResult?.status === "failed") {
    return "Итог основан только на основном тикере.";
  }

  return "Когда бенчмарк вернет свечи, здесь появится относительная доходность.";
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

function formatResultLabel(value) {
  if (!value) {
    return "-";
  }

  const labels = {
    supports: "Поддерживает гипотезу",
    mixed_support: "Смешанный результат",
    contradicts: "Противоречит гипотезе",
    insufficient_data: "Недостаточно данных",
    outperformed: "Лучше бенчмарка",
    underperformed: "Хуже бенчмарка",
    in_line: "В рамках бенчмарка",
    ok: "Ок",
    failed: "Ошибка",
    low: "низкая",
    medium: "средняя",
    high: "высокая",
    positive: "позитивный",
    negative: "негативный",
    mixed: "смешанный",
    neutral: "нейтральный",
    fundamental_logic: "фундаментальная логика",
    market_context: "рыночный контекст",
    risk: "риск",
    historical_validation: "историческая проверка",
    above: "выше",
    below: "ниже",
    watch: "наблюдение",
  };

  return labels[value] || value.replaceAll("_", " ");
}

function getTone(value) {
  const numberValue = Number(value);

  if (Number.isNaN(numberValue) || numberValue === 0) {
    return undefined;
  }

  return numberValue > 0 ? "positive" : "negative";
}
