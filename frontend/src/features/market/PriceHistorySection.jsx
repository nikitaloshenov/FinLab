import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

const CHART_WIDTH = 720;
const CHART_HEIGHT = 220;
const CHART_PADDING = 24;

export function PriceHistorySection({
  selectedTicker,
  priceHistory,
  isLoading,
  errorMessage,
  onReload,
}) {
  const latestPoints = priceHistory.slice(-8).reverse();

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

        <button
          type="button"
          disabled={!selectedTicker || isLoading}
          onClick={onReload}
        >
          {isLoading ? "Loading..." : "Reload history"}
        </button>
      </div>

      {!selectedTicker && (
        <p className="status">Тикер для истории пока не выбран.</p>
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
        <p className="status">Истории цен для выбранного тикера пока нет.</p>
      )}

      {selectedTicker && !isLoading && !errorMessage && priceHistory.length > 0 && (
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
      )}
    </section>
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
  const lastPoint = coordinates[coordinates.length - 1];

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

      <div className="priceChartMeta">
        <span>Min: {formatPrice(minValue)}</span>
        <span>Max: {formatPrice(maxValue)}</span>
        <span>Latest: {formatPrice(lastPoint.value)}</span>
      </div>
    </div>
  );
}
