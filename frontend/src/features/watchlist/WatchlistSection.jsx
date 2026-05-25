import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function WatchlistSection({
  watchlist,
  newTicker,
  onNewTickerChange,
  onAddTicker,
  onDeleteTicker,
  onRefreshTicker,
  onRefreshAllPrices,
  isLoading,
  isActionLoading,
  isRefreshAllLoading,
  refreshingTickers,
  errorMessage,
}) {
  const hasWatchlistItems = watchlist.length > 0;

  return (
    <section className="card">
      <div className="cardHeader">
        <div>
          <h2>Watchlist</h2>
          <p>Тикеры, которые сейчас отслеживаются в системе.</p>
        </div>

        <button
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

        <button type="submit" disabled={isActionLoading || isRefreshAllLoading}>
          {isActionLoading ? "Loading..." : "Add ticker"}
        </button>
      </form>

      {isLoading && <p className="status">Загрузка watchlist...</p>}

      {!isLoading && !errorMessage && watchlist.length === 0 && (
        <p className="status">Watchlist пока пустой.</p>
      )}

      {!isLoading && watchlist.length > 0 && (
        <div className="tableWrapper">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Last price</th>
                <th>Added at</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {watchlist.map((item) => {
                const isTickerRefreshing = refreshingTickers.includes(
                  item.secid
                );

                return (
                  <tr key={item.id}>
                    <td className="ticker">{item.secid}</td>
                    <td>{item.short_name || "—"}</td>
                    <td>{formatPrice(item.latest_price)}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <div className="rowActions">
                        <button
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
