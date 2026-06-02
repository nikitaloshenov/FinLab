import { useEffect, useState } from "react";

import { AlertEventsSection } from "../features/alerts/AlertEventsSection.jsx";
import { AlertsSection } from "../features/alerts/AlertsSection.jsx";
import {
  checkActiveAlerts,
  checkAlert,
  createAlert,
  deleteAlert,
  getAlertEvents,
  getAlerts,
} from "../features/alerts/api.js";
import {
  getTickerCandles,
  refreshTickerPrice,
} from "../features/market/api.js";
import { HypothesisLabSection } from "../features/hypotheses/HypothesisLabSection.jsx";
import { MarketChartSection } from "../features/market/MarketChartSection.jsx";
import { MarketOverviewSection } from "../features/market/MarketOverviewSection.jsx";
import { WatchlistSection } from "../features/watchlist/WatchlistSection.jsx";
import {
  addWatchlistItem,
  deleteWatchlistItem,
  getWatchlist,
  refreshWatchlistPrices,
} from "../features/watchlist/api.js";
import {
  buildAlertBatchCheckMessage,
  buildWatchlistRefreshMessage,
} from "../shared/lib/batchMessages.js";

export function MarketPage() {
  const [watchlist, setWatchlist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertEvents, setAlertEvents] = useState([]);
  const [candles, setCandles] = useState([]);

  const [newTicker, setNewTicker] = useState("");
  const [selectedTicker, setSelectedTicker] = useState("");
  const [candleInterval, setCandleInterval] = useState("1d");
  const [candleLimit, setCandleLimit] = useState(100);

  const [alertTicker, setAlertTicker] = useState("");
  const [alertCondition, setAlertCondition] = useState("above");
  const [alertTargetPrice, setAlertTargetPrice] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [isRefreshAllLoading, setIsRefreshAllLoading] = useState(false);
  const [isCheckingAllAlerts, setIsCheckingAllAlerts] = useState(false);
  const [isCandlesLoading, setIsCandlesLoading] = useState(false);

  const [refreshingTickers, setRefreshingTickers] = useState([]);
  const [checkingAlerts, setCheckingAlerts] = useState([]);

  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [candlesErrorMessage, setCandlesErrorMessage] = useState("");

  async function loadWatchlist({ showLoader = true } = {}) {
    try {
      if (showLoader) {
        setIsLoading(true);
      }

      setErrorMessage("");

      const data = await getWatchlist();

      setWatchlist(data);
      return data;
    } catch (error) {
      setErrorMessage(error.message);
      return [];
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

  async function loadTickerCandles(
    secid,
    interval = candleInterval,
    limit = candleLimit
  ) {
    if (!secid) {
      setCandles([]);
      setCandlesErrorMessage("");
      return [];
    }

    try {
      setIsCandlesLoading(true);
      setCandlesErrorMessage("");

      const data = await getTickerCandles(secid, { interval, limit });

      setCandles(data);
      return data;
    } catch (error) {
      setCandles([]);
      setCandlesErrorMessage(error.message);
      return [];
    } finally {
      setIsCandlesLoading(false);
    }
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

      const initialTicker = selectedTicker || watchlistData[0]?.secid || "";

      if (initialTicker) {
        setSelectedTicker(initialTicker);
        await loadTickerCandles(initialTicker, candleInterval, candleLimit);
      }
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
      setSelectedTicker(normalizedTicker);
      await loadTickerCandles(normalizedTicker, candleInterval, candleLimit);

      setInfoMessage(`${normalizedTicker} добавлен в watchlist.`);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleQuickAddTicker(secid) {
    const normalizedTicker = secid.trim().toUpperCase();
    const existingItem = watchlist.find((item) => item.secid === normalizedTicker);

    if (existingItem) {
      await handleSelectTicker(normalizedTicker);
      return;
    }

    try {
      setIsActionLoading(true);
      setErrorMessage("");
      setInfoMessage("");

      await addWatchlistItem(normalizedTicker);

      const updatedWatchlist = await loadWatchlist({ showLoader: false });

      setSelectedTicker(normalizedTicker);
      await loadTickerCandles(normalizedTicker, candleInterval, candleLimit);

      const addedItem = updatedWatchlist.find(
        (item) => item.secid === normalizedTicker
      );

      setInfoMessage(
        `${addedItem?.secid || normalizedTicker} добавлен в watchlist.`
      );
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

      const updatedWatchlist = await loadWatchlist({ showLoader: false });

      if (selectedTicker === secid) {
        const nextTicker = updatedWatchlist[0]?.secid || "";

        setSelectedTicker(nextTicker);

        if (nextTicker) {
          await loadTickerCandles(nextTicker, candleInterval, candleLimit);
        } else {
          setCandles([]);
          setCandlesErrorMessage("");
        }
      }

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

      const result = await refreshWatchlistPrices();

      await loadWatchlist({ showLoader: false });

      setInfoMessage(buildWatchlistRefreshMessage(result));
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

  async function handleCheckAllActiveAlerts() {
    const activeAlerts = alerts.filter((alert) => alert.is_active);

    if (activeAlerts.length === 0) {
      setInfoMessage("Активных alert’ов для проверки нет.");
      return;
    }

    const activeAlertIds = activeAlerts.map((alert) => alert.id);

    try {
      setErrorMessage("");
      setInfoMessage("");
      setIsCheckingAllAlerts(true);
      setCheckingAlerts(activeAlertIds);

      const result = await checkActiveAlerts();

      await Promise.all([loadAlerts(), loadAlertEvents()]);

      setInfoMessage(buildAlertBatchCheckMessage(result));
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsCheckingAllAlerts(false);
      setCheckingAlerts([]);
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

  async function handleSelectTicker(secid) {
    setSelectedTicker(secid);
    await loadTickerCandles(secid, candleInterval, candleLimit);
  }

  async function handleCandleIntervalChange(interval) {
    setCandleInterval(interval);

    if (selectedTicker) {
      await loadTickerCandles(selectedTicker, interval, candleLimit);
    }
  }

  async function handleCandleLimitChange(limit) {
    setCandleLimit(limit);

    if (selectedTicker) {
      await loadTickerCandles(selectedTicker, candleInterval, limit);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">FinLab Dashboard</p>
          <h1>Market Watchlist & Alerts</h1>
          <p className="heroText">
            Рабочая панель для MOEX-тикеров: watchlist, latest price,
            свечной Market Chart и price alerts в одном интерфейсе.
          </p>
        </div>
        <div className="heroMeta">
          <span>MOEX candles</span>
          <strong>{selectedTicker || "No ticker selected"}</strong>
        </div>
      </section>

      <div className="messages">
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
      </div>

      <MarketOverviewSection
        watchlist={watchlist}
        alerts={alerts}
        alertEvents={alertEvents}
        selectedTicker={selectedTicker}
        candles={candles}
        isLoading={isLoading}
      />

      <div className="dashboardGrid">
        <div className="dashboardMain">
          <MarketChartSection
            selectedTicker={selectedTicker}
            candles={candles}
            candleInterval={candleInterval}
            candleLimit={candleLimit}
            isLoading={isCandlesLoading}
            errorMessage={candlesErrorMessage}
            onIntervalChange={handleCandleIntervalChange}
            onLimitChange={handleCandleLimitChange}
            onReload={() =>
              loadTickerCandles(selectedTicker, candleInterval, candleLimit)
            }
          />
        </div>

        <div className="dashboardSide">
          <WatchlistSection
            watchlist={watchlist}
            newTicker={newTicker}
            onNewTickerChange={setNewTicker}
            onAddTicker={handleAddTicker}
            onDeleteTicker={handleDeleteTicker}
            onRefreshTicker={handleRefreshTicker}
            onRefreshAllPrices={handleRefreshAllPrices}
            onQuickAddTicker={handleQuickAddTicker}
            onSelectTicker={handleSelectTicker}
            isLoading={isLoading}
            isActionLoading={isActionLoading}
            isRefreshAllLoading={isRefreshAllLoading}
            refreshingTickers={refreshingTickers}
            selectedTicker={selectedTicker}
            errorMessage={errorMessage}
          />
        </div>
      </div>

      <HypothesisLabSection
        selectedTicker={selectedTicker}
        watchlist={watchlist}
      />

      <AlertsSection
        alerts={alerts}
        alertTicker={alertTicker}
        alertCondition={alertCondition}
        alertTargetPrice={alertTargetPrice}
        onAlertTickerChange={setAlertTicker}
        onAlertConditionChange={setAlertCondition}
        onAlertTargetPriceChange={setAlertTargetPrice}
        onCreateAlert={handleCreateAlert}
        onCheckAlert={handleCheckAlert}
        onCheckAllActiveAlerts={handleCheckAllActiveAlerts}
        onDeleteAlert={handleDeleteAlert}
        isLoading={isLoading}
        isActionLoading={isActionLoading}
        isCheckingAllAlerts={isCheckingAllAlerts}
        checkingAlerts={checkingAlerts}
      />

      <AlertEventsSection alertEvents={alertEvents} />
    </main>
  );
}
