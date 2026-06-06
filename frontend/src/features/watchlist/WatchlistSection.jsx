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
          <h2>Список наблюдения</h2>
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
          {isRefreshAllLoading ? "Обновляем..." : "Обновить цены"}
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
          {isActionLoading ? "Загрузка..." : "Добавить тикер"}
        </button>
      </form>

      <MarketUniverseQuickAdd
        watchlist={watchlist}
        onAddTicker={onQuickAddTicker}
        isDisabled={isActionLoading || isRefreshAllLoading}
      />

      {isLoading && (
        <div className="emptyState compact">
          <strong>Загрузка списка наблюдения</strong>
          <p>Получаем список отслеживаемых тикеров.</p>
        </div>
      )}

      {!isLoading && !errorMessage && watchlist.length === 0 && (
        <div className="emptyState compact">
          <strong>Список наблюдения пустой</strong>
          <p>Добавь тикер MOEX, чтобы начать мониторинг.</p>
        </div>
      )}

      {!isLoading && watchlist.length > 0 && (
        <div className="tableWrapper watchlistListWrapper">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Название</th>
                <th>Цена</th>
                <th>Действия</th>
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
                        <span>Добавлен {formatDate(item.created_at)}</span>
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
                          {isTickerRefreshing ? "..." : "Обновить"}
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
                          Удалить
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
