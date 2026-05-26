import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function MarketOverviewSection({
  watchlist,
  alerts,
  alertEvents,
  selectedTicker,
  priceHistory,
  isLoading,
}) {
  const watchlistItems = Array.isArray(watchlist) ? watchlist : [];
  const alertItems = Array.isArray(alerts) ? alerts : [];
  const eventItems = Array.isArray(alertEvents) ? alertEvents : [];
  const historyPoints = Array.isArray(priceHistory) ? priceHistory : [];

  const latestPoint = historyPoints[historyPoints.length - 1];
  const activeAlerts = alertItems.filter((alert) => alert?.is_active).length;

  return (
    <section className="card">
      <div className="cardHeader">
        <div>
          <h2>Market Overview</h2>
          <p>Краткое состояние watchlist, alert'ов и выбранного тикера.</p>
        </div>
      </div>

      <div className="overviewGrid">
        <OverviewCard
          label="Watchlist tickers"
          value={isLoading ? "..." : watchlistItems.length}
          hint="Всего отслеживается"
        />
        <OverviewCard
          label="Active alerts"
          value={isLoading ? "..." : activeAlerts}
          hint="Ожидают проверки"
        />
        <OverviewCard
          label="Latest selected price"
          value={latestPoint ? formatPrice(latestPoint.price) : "—"}
          hint={selectedTicker || "Тикер не выбран"}
        />
        <OverviewCard
          label="History points"
          value={historyPoints.length}
          hint={selectedTicker ? `Для ${selectedTicker}` : "Нет выбранного тикера"}
        />
        <OverviewCard
          label="Last update"
          value={latestPoint ? formatDate(latestPoint.received_at) : "—"}
          hint="Последняя сохраненная точка"
        />
        <OverviewCard
          label="Triggered events"
          value={isLoading ? "..." : eventItems.length}
          hint="История срабатываний"
        />
      </div>
    </section>
  );
}

function OverviewCard({ label, value, hint }) {
  return (
    <div className="overviewCard">
      <span className="overviewLabel">{label}</span>
      <strong className="overviewValue">{value}</strong>
      <span className="overviewHint">{hint}</span>
    </div>
  );
}
