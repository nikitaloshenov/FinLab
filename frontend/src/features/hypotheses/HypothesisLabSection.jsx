import { useEffect, useState } from "react";

import { analyzeHypothesis } from "./api.js";
import { HypothesisResultPanel } from "./HypothesisResultPanel.jsx";

const EVENT_DATE_PRESETS = {
  test_2026_05_15: {
    label: "15.05.2026 - тестовая дата",
    value: "2026-05-15",
  },
  custom: {
    label: "Своя дата",
    value: "",
  },
};

const BENCHMARK_OPTIONS = {
  none: {
    label: "Без бенчмарка",
    value: "",
    hint: "Сравнение с бенчмарком будет отключено.",
  },
  MOEX: {
    label: "MOEX - акция Московской биржи (временный proxy)",
    value: "MOEX",
    hint: "MOEX - это акция Московской биржи, не индекс рынка. Используется временно как ориентир, пока индексный benchmark не подключен.",
  },
  IMOEX: {
    label: "IMOEX - индекс Мосбиржи (может быть недоступен)",
    value: "IMOEX",
    hint: "Если MOEX ISS не вернет свечи индекса, отчет останется на уровне основного тикера.",
  },
};

const DEFAULT_FORM = {
  event_direction: "rate_cut",
  sector: "banks",
  main_ticker: "SBER",
  benchmark_ticker: "MOEX",
  event_date_mode: "test_2026_05_15",
  custom_event_date: "2026-05-15",
  window_before_days: 20,
  window_after_days: 20,
};

const BANKING_TICKERS = ["SBER", "SBERP", "VTBR", "T", "CBOM"];
const BROAD_MARKET_TICKERS = [
  "SBER",
  "GAZP",
  "LKOH",
  "ROSN",
  "NVTK",
  "YDEX",
  "GMKN",
  "T",
  "VTBR",
  "MOEX",
];

export function HypothesisLabSection({ selectedTicker, watchlist }) {
  const [formData, setFormData] = useState(DEFAULT_FORM);
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!selectedTicker) {
      return;
    }

    setFormData((currentFormData) => ({
      ...currentFormData,
      main_ticker:
        currentFormData.sector === "banks" &&
        !BANKING_TICKERS.includes(selectedTicker)
          ? "SBER"
          : selectedTicker,
    }));
  }, [selectedTicker]);

  function updateField(fieldName, value) {
    setFormData((currentFormData) => ({
      ...currentFormData,
      [fieldName]: value,
    }));
  }

  function selectMainTicker(secid) {
    setFormData((currentFormData) => ({
      ...currentFormData,
      main_ticker: secid,
    }));
  }

  function handleSectorChange(sector) {
    setFormData((currentFormData) => {
      const currentTicker = currentFormData.main_ticker.trim().toUpperCase();

      if (sector === "banks" && !BANKING_TICKERS.includes(currentTicker)) {
        return {
          ...currentFormData,
          sector,
          main_ticker: "SBER",
        };
      }

      return {
        ...currentFormData,
        sector,
      };
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const mainTicker = formData.main_ticker.trim().toUpperCase();
    const benchmarkTicker = formData.benchmark_ticker.trim().toUpperCase();
    const generatedHypothesis = buildGeneratedHypothesis({
      eventDirection: formData.event_direction,
      sector: formData.sector,
      mainTicker,
    });
    const eventDate = getEventDate(formData);

    if (!mainTicker) {
      setErrorMessage("Укажите основной тикер.");
      return;
    }

    if (!eventDate) {
      setErrorMessage("Укажите дату события.");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");

      const payload = {
        title: generatedHypothesis.title,
        user_hypothesis_text: generatedHypothesis.user_hypothesis_text,
        event_type: "key_rate",
        event_direction: formData.event_direction,
        sector: formData.sector,
        main_ticker: mainTicker,
        benchmark_ticker: benchmarkTicker || null,
        event_date: eventDate,
        interval: "1d",
        window_before_days: Number(formData.window_before_days),
        window_after_days: Number(formData.window_after_days),
        expected_direction: generatedHypothesis.expected_direction,
      };

      const data = await analyzeHypothesis(payload);

      setResult(data);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  const mainTicker = formData.main_ticker.trim().toUpperCase() || "SBER";
  const generatedHypothesis = buildGeneratedHypothesis({
    eventDirection: formData.event_direction,
    sector: formData.sector,
    mainTicker,
  });
  const quickTickers = getSectorQuickTickers({
    sector: formData.sector,
    watchlist,
  });
  const benchmarkHint =
    BENCHMARK_OPTIONS[formData.benchmark_ticker || "none"]?.hint ||
    BENCHMARK_OPTIONS.none.hint;

  return (
    <section className="card hypothesisSection">
      <div className="hypothesisHeader">
        <div>
          <p className="sectionKicker">Лаборатория гипотез</p>
          <h2>Анализ инвестиционной гипотезы</h2>
          <p>
            Выберите сценарий ставки, тикер и дату события. FinLab разложит
            гипотезу на механизмы влияния, проверит реакцию цены и покажет
            ограничения.
          </p>
        </div>
      </div>

      <div className="hypothesisLayout">
        <form className="hypothesisForm" onSubmit={handleSubmit}>
          <div className="hypothesisGrid">
            <label className="hypothesisField">
              <span>Сценарий ставки</span>
              <select
                value={formData.event_direction}
                onChange={(event) =>
                  updateField("event_direction", event.target.value)
                }
              >
                <option value="rate_cut">Снижение ключевой ставки</option>
                <option value="rate_hike">Повышение ключевой ставки</option>
              </select>
            </label>

            <label className="hypothesisField">
              <span>Объект анализа</span>
              <select
                value={formData.sector}
                onChange={(event) => handleSectorChange(event.target.value)}
              >
                <option value="banks">Банки и финансы</option>
                <option value="broad_market">Широкий рынок</option>
              </select>
            </label>

            <label className="hypothesisField">
              <span>Основной тикер</span>
              <input
                value={formData.main_ticker}
                onChange={(event) =>
                  updateField("main_ticker", event.target.value)
                }
                placeholder="SBER"
              />
            </label>

            <label className="hypothesisField">
              <span>Дата события</span>
              <select
                value={formData.event_date_mode}
                onChange={(event) =>
                  updateField("event_date_mode", event.target.value)
                }
              >
                {Object.entries(EVENT_DATE_PRESETS).map(([id, preset]) => (
                  <option key={id} value={id}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>

            {formData.event_date_mode === "custom" && (
              <label className="hypothesisField">
                <span>Своя дата</span>
                <input
                  type="date"
                  value={formData.custom_event_date}
                  onChange={(event) =>
                    updateField("custom_event_date", event.target.value)
                  }
                />
              </label>
            )}

            <label className="hypothesisField">
              <span>Бенчмарк</span>
              <select
                value={formData.benchmark_ticker}
                onChange={(event) =>
                  updateField("benchmark_ticker", event.target.value)
                }
              >
                {Object.entries(BENCHMARK_OPTIONS).map(([id, option]) => (
                  <option key={id} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="hypothesisField">
              <span>Дней до события</span>
              <input
                type="number"
                min="1"
                max="365"
                value={formData.window_before_days}
                onChange={(event) =>
                  updateField("window_before_days", event.target.value)
                }
              />
            </label>

            <label className="hypothesisField">
              <span>Дней после события</span>
              <input
                type="number"
                min="1"
                max="365"
                value={formData.window_after_days}
                onChange={(event) =>
                  updateField("window_after_days", event.target.value)
                }
              />
            </label>
          </div>

          <p className="hypothesisHint">
            Пока дата выбирается вручную. Позже здесь будет список исторических
            решений по ключевой ставке.
          </p>
          <p className="hypothesisHint">{benchmarkHint}</p>

          <div className="hypothesisPreview">
            <span>Текущая гипотеза</span>
            <strong>{generatedHypothesis.title}</strong>
            <p>{generatedHypothesis.user_hypothesis_text}</p>
          </div>

          {quickTickers.length > 0 && (
            <div className="hypothesisTickerChips">
              <span>Быстрый выбор по объекту анализа:</span>
              {quickTickers.map((item) => (
                <button
                  className={
                    mainTicker === item.secid
                      ? "tickerChip active"
                      : "tickerChip"
                  }
                  key={item.secid}
                  type="button"
                  onClick={() => selectMainTicker(item.secid)}
                >
                  {item.secid}
                </button>
              ))}
            </div>
          )}

          {errorMessage && (
            <div className="error hypothesisError">
              <strong>Ошибка анализа</strong>
              <p>{errorMessage}</p>
            </div>
          )}

          <div className="hypothesisActions">
            <button className="primaryButton" type="submit" disabled={isLoading}>
              {isLoading ? "Запускаем анализ..." : "Запустить анализ"}
            </button>
          </div>
        </form>

        <HypothesisResultPanel result={result} isLoading={isLoading} />
      </div>
    </section>
  );
}

function buildGeneratedHypothesis({ eventDirection, sector, mainTicker }) {
  const ticker = mainTicker || "SBER";

  if (eventDirection === "rate_cut" && sector === "banks") {
    return {
      title: `Снижение ставки и банки: ${ticker}`,
      user_hypothesis_text:
        "Проверяем гипотезу, что снижение ключевой ставки может поддержать выбранную банковскую/финансовую акцию.",
      expected_direction: "positive",
    };
  }

  if (eventDirection === "rate_hike" && sector === "banks") {
    return {
      title: `Повышение ставки и банки: ${ticker}`,
      user_hypothesis_text:
        "Проверяем гипотезу, что повышение ключевой ставки может создать давление на выбранную банковскую/финансовую акцию.",
      expected_direction: "negative",
    };
  }

  if (eventDirection === "rate_cut" && sector === "broad_market") {
    return {
      title: `Снижение ставки и широкий рынок: ${ticker}`,
      user_hypothesis_text:
        "Проверяем гипотезу, что снижение ключевой ставки может поддержать широкий рынок акций.",
      expected_direction: "positive",
    };
  }

  return {
    title: `Повышение ставки и широкий рынок: ${ticker}`,
    user_hypothesis_text:
      "Проверяем гипотезу, что повышение ключевой ставки может создать давление на широкий рынок акций.",
    expected_direction: "negative",
  };
}

function getEventDate(formData) {
  if (formData.event_date_mode === "custom") {
    return formData.custom_event_date;
  }

  return EVENT_DATE_PRESETS[formData.event_date_mode]?.value || "";
}

function getSectorQuickTickers({ sector, watchlist }) {
  const allowedTickers =
    sector === "banks" ? BANKING_TICKERS : BROAD_MARKET_TICKERS;
  const watchlistNames = new Map(
    watchlist.map((item) => [item.secid, item.short_name || item.secid]),
  );

  return allowedTickers.map((secid) => ({
    secid,
    name: watchlistNames.get(secid) || secid,
  }));
}
