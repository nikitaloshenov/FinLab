import { useEffect, useState } from "react";

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

  const [errorMessage, setErrorMessage] = useState("");

  async function loadWatchlist() {
    try {
      setIsLoading(true);
      setErrorMessage("");

      const data = await getWatchlist();

      setWatchlist(data);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsLoading(false);
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
      await loadWatchlist();
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

      await loadWatchlist();
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">FinLab</p>
        <h1>Market Watchlist</h1>
        <p className="heroText">
          Frontend уже работает с FastAPI backend: загружает watchlist, добавляет
          тикеры и удаляет их из списка.
        </p>
      </section>

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2>Watchlist</h2>
            <p>Тикеры, которые сейчас отслеживаются в системе.</p>
          </div>
        </div>

        <form className="tickerForm" onSubmit={handleAddTicker}>
          <input
            value={newTicker}
            onChange={(event) => setNewTicker(event.target.value)}
            placeholder="Например: SBER"
            disabled={isActionLoading}
          />

          <button type="submit" disabled={isActionLoading}>
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
                {watchlist.map((item) => (
                  <tr key={item.id}>
                    <td className="ticker">{item.secid}</td>
                    <td>{item.short_name || "—"}</td>
                    <td>{item.latest_price || "—"}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <button
                        className="dangerButton"
                        type="button"
                        disabled={isActionLoading}
                        onClick={() => handleDeleteTicker(item.secid)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
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