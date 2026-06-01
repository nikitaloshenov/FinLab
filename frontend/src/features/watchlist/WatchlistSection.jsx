import { formatDate, formatPrice } from "../../shared/lib/formatters.js";
import { MarketUniverseQuickAdd } from "./MarketUniverseQuickAdd.jsx";

export function WatchlistSection({
  watchlist,
  newTicker,
  onNewTickerChange,
  onAddTicker,
  onDeleteTicker,
  onRefreshTicker,
  onRefreshAllPrices,
  onQuickAddTicker,
  onSelectTicker,
  isLoading,
  isActionLoading,
  isRefreshAllLoading,
  refreshingTickers,
  selectedTicker,
  errorMessage,
}) {
  const hasWatchlistItems = watchlist.length > 0;

  return (
    <section className="card watchlistCard">
      <div className="cardHeader">
        <div>
          <h2>Watchlist</h2>
          <p>Тикеры, которые сейчас отслеживаются в системе.</p>
        </div>

        <button
          className="secondaryButton"
          type="button"
          disabled={
            isLoading ||
            isActionLoading ||
            isRefreshAllLoading ||
            !hasWatchlistItems
          }
          onClick={onRefreshAllPrices}
        >
          {isRefreshAllLoading ? "Refreshing..." : "Refresh all prices"}
        </button>
      </div>

      <form className="tickerForm" onSubmit={onAddTicker}>
        <input
          value={newTicker}
          onChange={(event) => onNewTickerChange(event.target.value)}
          placeholder="Например: SBER"
          disabled={isActionLoading || isRefreshAllLoading}
        />

        <button
          className="primaryButton"
          type="submit"
          disabled={isActionLoading || isRefreshAllLoading}
        >
          {isActionLoading ? "Loading..." : "Add ticker"}
        </button>
      </form>

      <MarketUniverseQuickAdd
        watchlist={watchlist}
        onAddTicker={onQuickAddTicker}
        isDisabled={isActionLoading || isRefreshAllLoading}
      />

      {isLoading && (
        <div className="emptyState compact">
          <strong>Загрузка watchlist</strong>
          <p>Получаем список отслеживаемых тикеров.</p>
        </div>
      )}

      {!isLoading && !errorMessage && watchlist.length === 0 && (
        <div className="emptyState compact">
          <strong>Watchlist пустой</strong>
          <p>Добавь тикер MOEX, чтобы начать мониторинг.</p>
        </div>
      )}

      {!isLoading && watchlist.length > 0 && (
        <div className="tableWrapper">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Last price</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {watchlist.map((item) => {
                const isTickerRefreshing = refreshingTickers.includes(
                  item.secid
                );

                return (
                  <tr
                    className={
                      item.secid === selectedTicker ? "table-row-active" : ""
                    }
                    key={item.id}
                  >
                    <td>
                      <button
                        className={
                          item.secid === selectedTicker
                            ? "tickerButton active"
                            : "tickerButton"
                        }
                        type="button"
                        onClick={() => onSelectTicker(item.secid)}
                      >
                        {item.secid}
                      </button>
                    </td>
                    <td>
                      <div className="stackedCell">
                        <strong>{item.short_name || "—"}</strong>
                        <span>Added {formatDate(item.created_at)}</span>
                      </div>
                    </td>
                    <td className="numericCell">{formatPrice(item.latest_price)}</td>
                    <td>
                      <div className="rowActions">
                        <button
                          className="subtleButton"
                          type="button"
                          disabled={
                            isActionLoading ||
                            isRefreshAllLoading ||
                            isTickerRefreshing
                          }
                          onClick={() => onRefreshTicker(item.secid)}
                        >
                          {isTickerRefreshing ? "..." : "Refresh"}
                        </button>

                        <button
                          className="dangerButton"
                          type="button"
                          disabled={
                            isActionLoading ||
                            isRefreshAllLoading ||
                            isTickerRefreshing
                          }
                          onClick={() => onDeleteTicker(item.secid)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
