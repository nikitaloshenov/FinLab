import { useEffect, useState } from "react";

import { refreshTickerPrice } from "../features/market/api.js";
import {
  addWatchlistItem,
  deleteWatchlistItem,
  getWatchlist,
} from "../features/watchlist/api.js";

export function MarketPage() {
  const [watchlist, setWatchlist] = useState([]);
  const [newTicker, setNewTicker] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [isRefreshAllLoading, setIsRefreshAllLoading] = useState(false);

  const [refreshingTickers, setRefreshingTickers] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadWatchlist({ showLoader = true } = {}) {
    try {
      if (showLoader) {
        setIsLoading(true);
      }

      setErrorMessage("");

      const data = await getWatchlist();

      setWatchlist(data);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      if (showLoader) {
        setIsLoading(false);
      }
    }
  }

  useEffect(() => {
    loadWatchlist();
  }, []);

  async function handleAddTicker(event) {
    event.preventDefault();

    const normalizedTicker = newTicker.trim().toUpperCase();

    if (!normalizedTicker) {
      setErrorMessage("Введите тикер.");
      return;
    }

    try {
      setIsActionLoading(true);
      setErrorMessage("");

      await addWatchlistItem(normalizedTicker);

      setNewTicker("");
      await loadWatchlist({ showLoader: false });
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleDeleteTicker(secid) {
    try {
      setIsActionLoading(true);
      setErrorMessage("");

      await deleteWatchlistItem(secid);

      await loadWatchlist({ showLoader: false });
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleRefreshTicker(secid) {
    try {
      setErrorMessage("");
      setRefreshingTickers((currentTickers) => [...currentTickers, secid]);

      await refreshTickerPrice(secid);
      await loadWatchlist({ showLoader: false });
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setRefreshingTickers((currentTickers) =>
        currentTickers.filter((ticker) => ticker !== secid)
      );
    }
  }

  async function handleRefreshAllPrices() {
    if (watchlist.length === 0) {
      return;
    }

    const tickers = watchlist.map((item) => item.secid);

    try {
      setErrorMessage("");
      setIsRefreshAllLoading(true);
      setRefreshingTickers(tickers);

      await Promise.all(
        tickers.map((secid) => refreshTickerPrice(secid))
      );

      await loadWatchlist({ showLoader: false });
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsRefreshAllLoading(false);
      setRefreshingTickers([]);
    }
  }

  const hasWatchlistItems = watchlist.length > 0;

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">FinLab</p>
        <h1>Market Watchlist</h1>
        <p className="heroText">
          Frontend уже работает с FastAPI backend: загружает watchlist, добавляет
          тикеры, удаляет их и обновляет цены через MOEX.
        </p>
      </section>

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
            onClick={handleRefreshAllPrices}
          >
            {isRefreshAllLoading ? "Refreshing..." : "Refresh all prices"}
          </button>
        </div>

        <form className="tickerForm" onSubmit={handleAddTicker}>
          <input
            value={newTicker}
            onChange={(event) => setNewTicker(event.target.value)}
            placeholder="Например: SBER"
            disabled={isActionLoading || isRefreshAllLoading}
          />

          <button
            type="submit"
            disabled={isActionLoading || isRefreshAllLoading}
          >
            {isActionLoading ? "Loading..." : "Add ticker"}
          </button>
        </form>

        {isLoading && <p className="status">Загрузка watchlist...</p>}

        {errorMessage && (
          <div className="error">
            <strong>Ошибка</strong>
            <p>{errorMessage}</p>
          </div>
        )}

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
                            onClick={() => handleRefreshTicker(item.secid)}
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
                            onClick={() => handleDeleteTicker(item.secid)}
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
    </main>
  );
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString("ru-RU");
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return value;
  }

  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numberValue);
}