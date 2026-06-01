import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

const CHART_WIDTH = 920;
const CHART_HEIGHT = 360;
const CHART_PADDING = {
  top: 24,
  right: 28,
  bottom: 46,
  left: 72,
};

export function MarketChartSection({
  selectedTicker,
  candles,
  candleInterval,
  candleLimit,
  isLoading,
  errorMessage,
  onIntervalChange,
  onLimitChange,
  onReload,
}) {
  const candleItems = Array.isArray(candles) ? candles : [];
  const latestCandles = candleItems.slice(-6).reverse();
  const stats = candleItems.length > 0 ? getCandleStats(candleItems) : null;

  return (
    <section className="card marketChartCard">
      <div className="cardHeader">
        <div>
          <h2>Market Chart</h2>
          <p>
            {selectedTicker
              ? `Свечи MOEX для выбранного тикера: ${selectedTicker}.`
              : "Выбери тикер в watchlist, чтобы открыть рыночный график."}
          </p>
        </div>

        <div className="chartToolbar">
          <label>
            <span>Interval</span>
            <select
              value={candleInterval}
              disabled={!selectedTicker || isLoading}
              onChange={(event) => onIntervalChange(event.target.value)}
            >
              <option value="10m">10m</option>
              <option value="1h">1h</option>
              <option value="1d">1d</option>
            </select>
          </label>

          <label>
            <span>Candles</span>
            <select
              value={candleLimit}
              disabled={!selectedTicker || isLoading}
              onChange={(event) => onLimitChange(Number(event.target.value))}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={250}>250</option>
            </select>
          </label>

          <button
            className="secondaryButton"
            type="button"
            disabled={!selectedTicker || isLoading}
            onClick={onReload}
          >
            {isLoading ? "Loading..." : "Reload chart"}
          </button>
        </div>
      </div>

      <p className="sectionHint">Source: MOEX candles</p>

      {!selectedTicker && (
        <div className="emptyState">
          <strong>Выбери тикер</strong>
          <p>Кликни по тикеру в watchlist, чтобы построить Market Chart.</p>
        </div>
      )}

      {selectedTicker && errorMessage && (
        <div className="error chartMessage">
          <strong>Ошибка</strong>
          <p>{errorMessage}</p>
        </div>
      )}

      {selectedTicker && isLoading && (
        <div className="emptyState">
          <strong>Загрузка свечей</strong>
          <p>Получаем MOEX candles для выбранного интервала.</p>
        </div>
      )}

      {selectedTicker && !isLoading && !errorMessage && candleItems.length === 0 && (
        <div className="emptyState">
          <strong>Свечей нет</strong>
          <p>MOEX не вернул свечи для выбранного тикера и интервала.</p>
        </div>
      )}

      {selectedTicker && !isLoading && !errorMessage && candleItems.length > 0 && stats && (
        <>
          <div className="chartStats">
            <StatItem label="Latest" value={formatPrice(stats.latestClose)} />
            <StatItem
              label="Change"
              value={formatSignedPrice(stats.change)}
              tone={stats.change >= 0 ? "positive" : "negative"}
            />
            <StatItem
              label="Change %"
              value={formatPercent(stats.changePercent)}
              tone={stats.change >= 0 ? "positive" : "negative"}
            />
            <StatItem label="Min close" value={formatPrice(stats.minClose)} />
            <StatItem label="Max close" value={formatPrice(stats.maxClose)} />
            <StatItem label="Candles" value={stats.count} />
          </div>

          <div className="marketChartLayout">
            <MarketLineChart candles={candleItems} interval={candleInterval} />

            <div className="candlesPanel">
              <div className="panelTitle">
                <span>Latest candles</span>
                <strong>{latestCandles.length}</strong>
              </div>

              <div className="tableWrapper candlesTable">
                <table>
                  <thead>
                    <tr>
                      <th>Begin</th>
                      <th>Open</th>
                      <th>High</th>
                      <th>Low</th>
                      <th>Close</th>
                      <th>Volume</th>
                    </tr>
                  </thead>

                  <tbody>
                    {latestCandles.map((candle) => (
                      <tr key={`${candle.begin}-${candle.close}`}>
                        <td>{formatCandleTime(candle.begin, candleInterval)}</td>
                        <td>{formatPrice(candle.open)}</td>
                        <td>{formatPrice(candle.high)}</td>
                        <td>{formatPrice(candle.low)}</td>
                        <td>{formatPrice(candle.close)}</td>
                        <td>{formatPrice(candle.volume)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function StatItem({ label, value, tone }) {
  const className = tone ? `chartStat ${tone}` : "chartStat";

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MarketLineChart({ candles, interval }) {
  const values = candles.map((candle) => Number(candle.close));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const paddingValue = minValue === maxValue ? Math.max(minValue * 0.01, 1) : 0;
  const axisMin = minValue - paddingValue;
  const axisMax = maxValue + paddingValue;
  const valueRange = axisMax - axisMin || 1;
  const drawableWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
  const drawableHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;

  const coordinates = values.map((value, index) => {
    const x =
      candles.length === 1
        ? CHART_PADDING.left + drawableWidth / 2
        : CHART_PADDING.left + (index / (candles.length - 1)) * drawableWidth;
    const ratio = (value - axisMin) / valueRange;
    const y = CHART_HEIGHT - CHART_PADDING.bottom - ratio * drawableHeight;

    return { x, y, value };
  });

  const linePoints = coordinates.map((point) => `${point.x},${point.y}`).join(" ");
  const yTicks = buildYTicks(axisMin, axisMax);
  const xTicks = buildXTicks(candles);
  const firstPoint = coordinates[0];

  return (
    <div className="priceChart">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        role="img"
        aria-label="MOEX candles close price chart"
      >
        {yTicks.map((tick) => {
          const ratio = (tick - axisMin) / valueRange;
          const y = CHART_HEIGHT - CHART_PADDING.bottom - ratio * drawableHeight;

          return (
            <g key={tick}>
              <line
                className="priceChartGrid"
                x1={CHART_PADDING.left}
                y1={y}
                x2={CHART_WIDTH - CHART_PADDING.right}
                y2={y}
              />
              <text className="priceChartLabel" x={CHART_PADDING.left - 10} y={y + 4}>
                {formatPrice(tick)}
              </text>
            </g>
          );
        })}

        {xTicks.map((tick) => {
          const x =
            candles.length === 1
              ? CHART_PADDING.left + drawableWidth / 2
              : CHART_PADDING.left + (tick.index / (candles.length - 1)) * drawableWidth;

          return (
            <g key={`${tick.index}-${tick.label}`}>
              <line
                className="priceChartGrid vertical"
                x1={x}
                y1={CHART_PADDING.top}
                x2={x}
                y2={CHART_HEIGHT - CHART_PADDING.bottom}
              />
              <text className="priceChartXLabel" x={x} y={CHART_HEIGHT - 14}>
                {formatCandleTime(tick.begin, interval)}
              </text>
            </g>
          );
        })}

        {coordinates.length > 1 ? (
          <polyline className="priceChartLine" points={linePoints} />
        ) : (
          <circle
            className="priceChartPoint"
            cx={firstPoint.x}
            cy={firstPoint.y}
            r="5"
          />
        )}

        {coordinates.length > 1 &&
          coordinates.map((point) => (
            <circle
              className="priceChartPoint"
              key={`${point.x}-${point.y}`}
              cx={point.x}
              cy={point.y}
              r="2.5"
            />
          ))}
      </svg>
    </div>
  );
}

function getCandleStats(candles) {
  const closeValues = candles.map((candle) => Number(candle.close));
  const firstClose = closeValues[0];
  const latestClose = closeValues[closeValues.length - 1];
  const change = latestClose - firstClose;
  const changePercent = firstClose === 0 ? 0 : (change / firstClose) * 100;

  return {
    count: candles.length,
    minClose: Math.min(...closeValues),
    maxClose: Math.max(...closeValues),
    latestClose,
    change,
    changePercent,
  };
}

function buildYTicks(minValue, maxValue) {
  const ticks = [];
  const tickCount = 5;
  const step = (maxValue - minValue) / (tickCount - 1 || 1);

  for (let index = 0; index < tickCount; index += 1) {
    ticks.push(minValue + step * index);
  }

  return ticks;
}

function buildXTicks(candles) {
  if (candles.length === 1) {
    return [{ index: 0, begin: candles[0].begin }];
  }

  const indexes = [0, Math.floor((candles.length - 1) / 2), candles.length - 1];
  const uniqueIndexes = [...new Set(indexes)];

  return uniqueIndexes.map((index) => ({
    index,
    begin: candles[index].begin,
  }));
}

function formatCandleTime(value, interval) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  if (interval === "1d") {
    return date.toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
    });
  }

  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSignedPrice(value) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatPrice(value)}`;
}

function formatPercent(value) {
  const prefix = value > 0 ? "+" : "";

  return `${prefix}${new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)}%`;
}
