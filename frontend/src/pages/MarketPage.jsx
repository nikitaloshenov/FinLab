import { useEffect, useRef, useState } from "react";

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
import { getInstrumentReference } from "../features/reference/api.js";
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
import { isNetworkApiError } from "../shared/api/client.js";

const FOOTER_CONTACTS = {
  githubUrl: "https://github.com/nikitaloshenov/FinLab",
  telegramUrl: "https://t.me/JIRNIYDIZAINER",
  telegramHandle: "@JIRNIYDIZAINER",
};

const STARTUP_RETRY_ATTEMPTS = 8;
const STARTUP_RETRY_DELAY_MS = 1250;

function wait(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

export function MarketPage() {
  const [watchlist, setWatchlist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertEvents, setAlertEvents] = useState([]);
  const [candles, setCandles] = useState([]);
  const [instrumentReferences, setInstrumentReferences] = useState({});

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
  const quickAddInFlightRef = useRef("");
  const alertCreateInFlightRef = useRef(false);

  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [candlesErrorMessage, setCandlesErrorMessage] = useState("");
  const [apiStartupStatus, setApiStartupStatus] = useState("idle");

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

  async function loadPageData({ retryStartup = true } = {}) {
    setIsLoading(true);
    setErrorMessage("");
    setApiStartupStatus("idle");

    try {
      const attempts = retryStartup ? STARTUP_RETRY_ATTEMPTS : 1;

      for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
          const [watchlistData, alertsData, alertEventsData] = await Promise.all([
            getWatchlist(),
            getAlerts(),
            getAlertEvents(),
          ]);

          setWatchlist(watchlistData);
          setAlerts(alertsData);
          setAlertEvents(alertEventsData);
          setApiStartupStatus("idle");

          const initialTicker = selectedTicker || watchlistData[0]?.secid || "";

          if (initialTicker) {
            setSelectedTicker(initialTicker);
            await loadTickerCandles(initialTicker, candleInterval, candleLimit);
          }

          return;
        } catch (error) {
          const canRetry =
            retryStartup && isNetworkApiError(error) && attempt < attempts;

          if (!canRetry) {
            if (retryStartup && isNetworkApiError(error)) {
              setApiStartupStatus("failed");
            } else {
              setApiStartupStatus("idle");
              setErrorMessage(error.message);
            }

            return;
          }

          setApiStartupStatus("connecting");
          await wait(STARTUP_RETRY_DELAY_MS);
        }
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadPageData();
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadInstrumentReferences() {
      const secids = [...new Set(watchlist.map((item) => item.secid))];

      if (secids.length === 0) {
        setInstrumentReferences({});
        return;
      }

      const results = await Promise.allSettled(
        secids.map(async (secid) => [secid, await getInstrumentReference(secid)])
      );

      if (isCancelled) {
        return;
      }

      const nextReferences = {};

      for (const result of results) {
        if (result.status === "fulfilled") {
          const [secid, reference] = result.value;
          nextReferences[secid] = reference;
        }
      }

      setInstrumentReferences(nextReferences);
    }

    loadInstrumentReferences();

    return () => {
      isCancelled = true;
    };
  }, [watchlist]);

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

      setInfoMessage(`${normalizedTicker} добавлен в список наблюдения.`);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleQuickAddTicker(secid) {
    const normalizedTicker = secid.trim().toUpperCase();

    if (quickAddInFlightRef.current) {
      return;
    }

    const existingItem = watchlist.find((item) => item.secid === normalizedTicker);

    if (existingItem) {
      await handleSelectTicker(normalizedTicker);
      return;
    }

    try {
      quickAddInFlightRef.current = normalizedTicker;
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
        `${addedItem?.secid || normalizedTicker} добавлен в список наблюдения.`
      );
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      quickAddInFlightRef.current = "";
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

      setInfoMessage(`${secid} удален из списка наблюдения.`);
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

    if (alertCreateInFlightRef.current) {
      return;
    }

    const normalizedTicker = alertTicker.trim().toUpperCase();
    const normalizedTargetPrice = alertTargetPrice.trim();
    const numericTargetPrice = Number(normalizedTargetPrice);

    if (!normalizedTicker) {
      setErrorMessage("Введите тикер для алерта.");
      return;
    }

    if (!["above", "below"].includes(alertCondition)) {
      setErrorMessage("Выберите корректное условие алерта.");
      return;
    }

    if (
      !normalizedTargetPrice ||
      Number.isNaN(numericTargetPrice) ||
      numericTargetPrice <= 0
    ) {
      setErrorMessage("Введите целевую цену больше 0.");
      return;
    }

    try {
      alertCreateInFlightRef.current = true;
      setIsActionLoading(true);
      setErrorMessage("");
      setInfoMessage("");

      const createdAlert = await createAlert({
        secid: normalizedTicker,
        condition: alertCondition,
        targetPrice: normalizedTargetPrice,
      });

      setAlertTicker("");
      setAlertCondition("above");
      setAlertTargetPrice("");

      let checkResult = null;

      if (createdAlert?.id) {
        setCheckingAlerts((currentAlerts) => [...currentAlerts, createdAlert.id]);

        try {
          checkResult = await checkAlert(createdAlert.id);
        } finally {
          setCheckingAlerts((currentAlerts) =>
            currentAlerts.filter((id) => id !== createdAlert.id)
          );
        }
      }

      await Promise.all([loadAlerts(), loadAlertEvents()]);

      if (checkResult?.triggered) {
        setInfoMessage(
          `Алерт для ${normalizedTicker} создан и сразу сработал.`
        );
      } else if (checkResult) {
        setInfoMessage(
          `Алерт для ${normalizedTicker} создан и проверен по последней цене.`
        );
      } else {
        setInfoMessage(`Алерт для ${normalizedTicker} создан.`);
      }
    } catch (error) {
      setErrorMessage(error.message);
      await Promise.all([loadAlerts(), loadAlertEvents()]);
    } finally {
      alertCreateInFlightRef.current = false;
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
          <h1>Панель рыночного анализа</h1>
          <p className="heroText">
            Рабочее пространство для MOEX-тикеров: список наблюдения, график,
            алерты и проверка рыночных гипотез.
          </p>
        </div>
      </section>

      <div className="messages">
        {apiStartupStatus === "connecting" && !errorMessage && (
          <div className="info pageMessage startupMessage">
            <strong>Сервер запускается. Подключаемся к API...</strong>
            <p>Обычно это занимает несколько секунд после запуска Docker.</p>
          </div>
        )}

        {apiStartupStatus === "failed" && !errorMessage && (
          <div className="error pageMessage startupMessage">
            <strong>Не удалось подключиться к API. Проверь, что backend запущен.</strong>
            <p>
              Если backend только стартует, попробуй повторить подключение через
              несколько секунд.
            </p>
            <button
              className="secondaryButton startupRetryButton"
              type="button"
              onClick={() => loadPageData({ retryStartup: true })}
            >
              Повторить
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="error pageMessage">
            <strong>Ошибка</strong>
            <p>{errorMessage}</p>
          </div>
        )}

        {infoMessage && !errorMessage && apiStartupStatus === "idle" && (
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
            instrumentReferences={instrumentReferences}
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

      <footer className="siteFooter">
        <div className="footerBrand">
          <strong>FinLab</strong>
          <p>Исторический анализ рынка. Не является инвестиционной рекомендацией.</p>
          <p className="footerSessionHint">
            Данные списка наблюдения и алертов привязаны к текущему браузеру.
          </p>
        </div>
        <div className="footerContacts">
          <a
            href={FOOTER_CONTACTS.githubUrl}
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <a
            href={FOOTER_CONTACTS.telegramUrl}
            target="_blank"
            rel="noreferrer"
          >
            Telegram: {FOOTER_CONTACTS.telegramHandle}
          </a>
        </div>
      </footer>
    </main>
  );
}
