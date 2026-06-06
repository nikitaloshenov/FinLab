import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function MarketOverviewSection({
  watchlist,
  alerts,
  alertEvents,
  selectedTicker,
  candles,
  isLoading,
}) {
  const watchlistItems = Array.isArray(watchlist) ? watchlist : [];
  const alertItems = Array.isArray(alerts) ? alerts : [];
  const eventItems = Array.isArray(alertEvents) ? alertEvents : [];
  const candleItems = Array.isArray(candles) ? candles : [];

  const latestCandle = candleItems[candleItems.length - 1];
  const activeAlerts = alertItems.filter((alert) => alert?.is_active).length;

  return (
    <section className="card overviewSection">
      <div className="cardHeader">
        <div>
          <h2>Обзор рынка</h2>
          <p>Краткое состояние списка наблюдения, алертов и выбранного тикера.</p>
        </div>
      </div>

      <div className="overviewGrid">
        <OverviewCard
          label="Тикеры"
          value={isLoading ? "..." : watchlistItems.length}
          hint="Всего отслеживается"
        />
        <OverviewCard
          label="Активные алерты"
          value={isLoading ? "..." : activeAlerts}
          hint="Ожидают проверки"
        />
        <OverviewCard
          label="Последняя цена"
          value={latestCandle ? formatPrice(latestCandle.close) : "—"}
          hint={selectedTicker || "Тикер не выбран"}
        />
        <OverviewCard
          label="Свечи"
          value={candleItems.length}
          hint={selectedTicker ? `Для ${selectedTicker}` : "Нет выбранного тикера"}
        />
        <OverviewCard
          label="Последнее обновление"
          value={latestCandle ? formatDate(latestCandle.begin) : "—"}
          hint="Последняя свеча MOEX"
        />
        <OverviewCard
          label="События алертов"
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
