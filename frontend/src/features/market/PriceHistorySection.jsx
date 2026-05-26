import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

const CHART_WIDTH = 720;
const CHART_HEIGHT = 220;
const CHART_PADDING = 24;

export function PriceHistorySection({
  selectedTicker,
  priceHistory,
  priceHistoryLimit,
  isLoading,
  errorMessage,
  onLimitChange,
  onReload,
}) {
  const latestPoints = priceHistory.slice(-8).reverse();
  const stats = getPriceHistoryStats(priceHistory);

  return (
    <section className="card">
      <div className="cardHeader">
        <div>
          <h2>Price History</h2>
          <p>
            {selectedTicker
              ? `История сохраненных цен для ${selectedTicker}.`
              : "Выбери тикер в watchlist, чтобы посмотреть историю."}
          </p>
        </div>

        <div className="priceHistoryControls">
          <label>
            <span>History points</span>
            <select
              value={priceHistoryLimit}
              disabled={!selectedTicker || isLoading}
              onChange={(event) => onLimitChange(Number(event.target.value))}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </label>

          <button
            type="button"
            disabled={!selectedTicker || isLoading}
            onClick={onReload}
          >
            {isLoading ? "Loading..." : "Reload history"}
          </button>
        </div>
      </div>

      {!selectedTicker && (
        <p className="status">Выбери тикер из watchlist, чтобы посмотреть историю цен.</p>
      )}

      {selectedTicker && errorMessage && (
        <div className="error priceHistoryMessage">
          <strong>Ошибка</strong>
          <p>{errorMessage}</p>
        </div>
      )}

      {selectedTicker && isLoading && (
        <p className="status">Загрузка истории цен...</p>
      )}

      {selectedTicker && !isLoading && !errorMessage && priceHistory.length === 0 && (
        <p className="status">
          Истории цен пока нет. Нажми Refresh у тикера, чтобы сохранить новую точку.
        </p>
      )}

      {selectedTicker && !isLoading && !errorMessage && priceHistory.length > 0 && (
        <>
          <div className="priceHistoryStats">
            <StatItem label="Points" value={stats.points} />
            <StatItem label="Min" value={formatPrice(stats.min)} />
            <StatItem label="Max" value={formatPrice(stats.max)} />
            <StatItem label="Latest" value={formatPrice(stats.latest)} />
          </div>

          <div className="priceHistoryLayout">
            <PriceHistoryChart points={priceHistory} />

            <div className="tableWrapper priceHistoryTable">
              <table>
                <thead>
                  <tr>
                    <th>Price</th>
                    <th>Source</th>
                    <th>Received</th>
                  </tr>
                </thead>

                <tbody>
                  {latestPoints.map((point) => (
                    <tr key={`${point.received_at}-${point.price}`}>
                      <td>{formatPrice(point.price)}</td>
                      <td>{point.source}</td>
                      <td>{formatDate(point.received_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function StatItem({ label, value }) {
  return (
    <div className="priceHistoryStat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PriceHistoryChart({ points }) {
  const values = points.map((point) => Number(point.price));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = maxValue - minValue;
  const drawableWidth = CHART_WIDTH - CHART_PADDING * 2;
  const drawableHeight = CHART_HEIGHT - CHART_PADDING * 2;

  const coordinates = values.map((value, index) => {
    const x =
      points.length === 1
        ? CHART_WIDTH / 2
        : CHART_PADDING + (index / (points.length - 1)) * drawableWidth;
    const ratio = valueRange === 0 ? 0.5 : (value - minValue) / valueRange;
    const y = CHART_HEIGHT - CHART_PADDING - ratio * drawableHeight;

    return { x, y, value };
  });

  const polylinePoints = coordinates
    .map((point) => `${point.x},${point.y}`)
    .join(" ");
  const firstPoint = coordinates[0];

  return (
    <div className="priceChart">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        role="img"
        aria-label="Price history chart"
      >
        <line
          className="priceChartGrid"
          x1={CHART_PADDING}
          y1={CHART_PADDING}
          x2={CHART_PADDING}
          y2={CHART_HEIGHT - CHART_PADDING}
        />
        <line
          className="priceChartGrid"
          x1={CHART_PADDING}
          y1={CHART_HEIGHT - CHART_PADDING}
          x2={CHART_WIDTH - CHART_PADDING}
          y2={CHART_HEIGHT - CHART_PADDING}
        />

        {coordinates.length > 1 ? (
          <polyline className="priceChartLine" points={polylinePoints} />
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
              r="3"
            />
          ))}
      </svg>
    </div>
  );
}

function getPriceHistoryStats(points) {
  const values = points.map((point) => Number(point.price));

  return {
    points: points.length,
    min: Math.min(...values),
    max: Math.max(...values),
    latest: values[values.length - 1],
  };
}
