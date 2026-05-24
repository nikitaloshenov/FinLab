import { useEffect, useState } from "react";

import {
  checkAlert,
  createAlert,
  deleteAlert,
  getAlertEvents,
  getAlerts,
} from "../features/alerts/api.js";
import { refreshTickerPrice } from "../features/market/api.js";
import {
  addWatchlistItem,
  deleteWatchlistItem,
  getWatchlist,
} from "../features/watchlist/api.js";

export function MarketPage() {
  const [watchlist, setWatchlist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertEvents, setAlertEvents] = useState([]);

  const [newTicker, setNewTicker] = useState("");

  const [alertTicker, setAlertTicker] = useState("");
  const [alertCondition, setAlertCondition] = useState("above");
  const [alertTargetPrice, setAlertTargetPrice] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [isRefreshAllLoading, setIsRefreshAllLoading] = useState(false);

  const [refreshingTickers, setRefreshingTickers] = useState([]);
  const [checkingAlerts, setCheckingAlerts] = useState([]);

  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

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

  async function loadAlerts() {
    const data = await getAlerts();
    setAlerts(data);
  }

  async function loadAlertEvents() {
    const data = await getAlertEvents();
    setAlertEvents(data);
  }

  async function loadPageData() {
    try {
      setIsLoading(true);
      setErrorMessage("");

      const [watchlistData, alertsData, alertEventsData] = await Promise.all([
        getWatchlist(),
        getAlerts(),
        getAlertEvents(),
      ]);

      setWatchlist(watchlistData);
      setAlerts(alertsData);
      setAlertEvents(alertEventsData);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadPageData();
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
      setInfoMessage("");

      await addWatchlistItem(normalizedTicker);

      setNewTicker("");
      await loadWatchlist({ showLoader: false });

      setInfoMessage(`${normalizedTicker} добавлен в watchlist.`);
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
      setInfoMessage("");

      await deleteWatchlistItem(secid);

      await loadWatchlist({ showLoader: false });

      setInfoMessage(`${secid} удален из watchlist.`);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleRefreshTicker(secid) {
    try {
      setErrorMessage("");
      setInfoMessage("");
      setRefreshingTickers((currentTickers) => [...currentTickers, secid]);

      await refreshTickerPrice(secid);
      await loadWatchlist({ showLoader: false });

      setInfoMessage(`${secid}: цена обновлена.`);
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
      setInfoMessage("");
      setIsRefreshAllLoading(true);
      setRefreshingTickers(tickers);

      await Promise.all(tickers.map((secid) => refreshTickerPrice(secid)));

      await loadWatchlist({ showLoader: false });

      setInfoMessage("Все цены обновлены.");
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsRefreshAllLoading(false);
      setRefreshingTickers([]);
    }
  }

  async function handleCreateAlert(event) {
    event.preventDefault();

    const normalizedTicker = alertTicker.trim().toUpperCase();
    const normalizedTargetPrice = alertTargetPrice.trim();

    if (!normalizedTicker) {
      setErrorMessage("Введите тикер для alert.");
      return;
    }

    if (!normalizedTargetPrice) {
      setErrorMessage("Введите целевую цену.");
      return;
    }

    try {
      setIsActionLoading(true);
      setErrorMessage("");
      setInfoMessage("");

      await createAlert({
        secid: normalizedTicker,
        condition: alertCondition,
        targetPrice: normalizedTargetPrice,
      });

      setAlertTicker("");
      setAlertCondition("above");
      setAlertTargetPrice("");

      await loadAlerts();

      setInfoMessage(`Alert для ${normalizedTicker} создан.`);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleCheckAlert(alertId) {
    try {
      setErrorMessage("");
      setInfoMessage("");
      setCheckingAlerts((currentAlerts) => [...currentAlerts, alertId]);

      const result = await checkAlert(alertId);

      await Promise.all([loadAlerts(), loadAlertEvents()]);

      setInfoMessage(result.message || "Alert проверен.");
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setCheckingAlerts((currentAlerts) =>
        currentAlerts.filter((id) => id !== alertId)
      );
    }
  }

  async function handleDeleteAlert(alertId) {
    try {
      setIsActionLoading(true);
      setErrorMessage("");
      setInfoMessage("");

      await deleteAlert(alertId);

      await Promise.all([loadAlerts(), loadAlertEvents()]);

      setInfoMessage(`Alert #${alertId} удален.`);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  const hasWatchlistItems = watchlist.length > 0;

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">FinLab</p>
        <h1>Market Watchlist</h1>
        <p className="heroText">
          Frontend работает с FastAPI backend: watchlist, обновление цен и
          price alerts.
        </p>
      </section>

      {errorMessage && (
        <div className="error pageMessage">
          <strong>Ошибка</strong>
          <p>{errorMessage}</p>
        </div>
      )}

      {infoMessage && !errorMessage && (
        <div className="success pageMessage">
          <strong>Готово</strong>
          <p>{infoMessage}</p>
        </div>
      )}

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

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2>Price Alerts</h2>
            <p>Создай правило: цена выше или ниже заданного уровня.</p>
          </div>
        </div>

        <form className="alertForm" onSubmit={handleCreateAlert}>
          <input
            value={alertTicker}
            onChange={(event) => setAlertTicker(event.target.value)}
            placeholder="Ticker: SBER"
            disabled={isActionLoading}
          />

          <select
            value={alertCondition}
            onChange={(event) => setAlertCondition(event.target.value)}
            disabled={isActionLoading}
          >
            <option value="above">above</option>
            <option value="below">below</option>
          </select>

          <input
            value={alertTargetPrice}
            onChange={(event) => setAlertTargetPrice(event.target.value)}
            placeholder="Target price"
            disabled={isActionLoading}
          />

          <button type="submit" disabled={isActionLoading}>
            {isActionLoading ? "Loading..." : "Create alert"}
          </button>
        </form>

        {alerts.length === 0 && (
          <p className="status">Активных или созданных alert’ов пока нет.</p>
        )}

        {alerts.length > 0 && (
          <div className="tableWrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Ticker</th>
                  <th>Condition</th>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {alerts.map((alert) => {
                  const isChecking = checkingAlerts.includes(alert.id);

                  return (
                    <tr key={alert.id}>
                      <td>#{alert.id}</td>
                      <td className="ticker">{alert.secid}</td>
                      <td>{alert.condition}</td>
                      <td>{formatPrice(alert.target_price)}</td>
                      <td>
                        <span
                          className={
                            alert.is_active ? "statusBadge" : "statusBadge muted"
                          }
                        >
                          {alert.is_active ? "active" : "inactive"}
                        </span>
                      </td>
                      <td>{formatDate(alert.created_at)}</td>
                      <td>
                        <div className="rowActions">
                          <button
                            type="button"
                            disabled={
                              isActionLoading ||
                              isChecking ||
                              !alert.is_active
                            }
                            onClick={() => handleCheckAlert(alert.id)}
                          >
                            {isChecking ? "..." : "Check"}
                          </button>

                          <button
                            className="dangerButton"
                            type="button"
                            disabled={isActionLoading || isChecking}
                            onClick={() => handleDeleteAlert(alert.id)}
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

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2>Alert Events</h2>
            <p>История срабатываний alert’ов.</p>
          </div>
        </div>

        {alertEvents.length === 0 && (
          <p className="status">Событий пока нет.</p>
        )}

        {alertEvents.length > 0 && (
          <div className="tableWrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Alert</th>
                  <th>Ticker</th>
                  <th>Price</th>
                  <th>Target</th>
                  <th>Condition</th>
                  <th>Created</th>
                </tr>
              </thead>

              <tbody>
                {alertEvents.map((event) => (
                  <tr key={event.id}>
                    <td>#{event.id}</td>
                    <td>#{event.alert_id}</td>
                    <td className="ticker">{event.secid}</td>
                    <td>{formatPrice(event.price)}</td>
                    <td>{formatPrice(event.target_price)}</td>
                    <td>{event.condition}</td>
                    <td>{formatDate(event.created_at)}</td>
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