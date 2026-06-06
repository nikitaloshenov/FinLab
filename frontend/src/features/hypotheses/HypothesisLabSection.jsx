import { useEffect, useState } from "react";

import { analyzeKeyRateImpact } from "./api.js";
import { HypothesisResultPanel } from "./HypothesisResultPanel.jsx";

const QUICK_TICKERS = [
  { secid: "SBER", name: "Сбербанк" },
  { secid: "SBERP", name: "Сбербанк-п" },
  { secid: "T", name: "Т-Банк" },
  { secid: "VTBR", name: "ВТБ" },
  { secid: "CBOM", name: "МКБ" },
  { secid: "MOEX", name: "Московская биржа" },
  { secid: "GAZP", name: "Газпром" },
  { secid: "LKOH", name: "Лукойл" },
  { secid: "ROSN", name: "Роснефть" },
  { secid: "NVTK", name: "Новатэк" },
  { secid: "YDEX", name: "Яндекс" },
];

const COMPANY_NAMES = {
  SBER: "Сбербанк",
  SBERP: "Сбербанк-п",
  T: "Т-Банк",
  VTBR: "ВТБ",
  CBOM: "МКБ",
  MOEX: "Московская биржа",
  GAZP: "Газпром",
  LKOH: "ЛУКОЙЛ",
  ROSN: "Роснефть",
  NVTK: "Новатэк",
  YDEX: "Яндекс",
};

const DIRECTION_OPTIONS = [
  { value: "rate_cut", label: "Снижение ставки" },
  { value: "rate_hike", label: "Повышение ставки" },
  { value: "rate_hold", label: "Сохранение ставки" },
];

const HORIZON_OPTIONS = [
  { value: 1, label: "1 торговый день" },
  { value: 3, label: "3 торговых дня" },
  { value: 10, label: "10 торговых дней" },
];

const DEFAULT_FORM = {
  main_ticker: "SBER",
  direction: "rate_cut",
  benchmark_ticker: "",
  horizons: [1, 3, 10],
  include_events: false,
};

export function HypothesisLabSection({ selectedTicker }) {
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
      main_ticker: selectedTicker.trim().toUpperCase(),
    }));
  }, [selectedTicker]);

  function updateField(fieldName, value) {
    setFormData((currentFormData) => ({
      ...currentFormData,
      [fieldName]: value,
    }));
  }

  function selectMainTicker(secid) {
    updateField("main_ticker", secid);
  }

  function toggleHorizon(horizon) {
    setFormData((currentFormData) => {
      const hasHorizon = currentFormData.horizons.includes(horizon);
      const nextHorizons = hasHorizon
        ? currentFormData.horizons.filter((item) => item !== horizon)
        : [...currentFormData.horizons, horizon].sort((left, right) => left - right);

      return {
        ...currentFormData,
        horizons: nextHorizons,
      };
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const mainTicker = formData.main_ticker.trim().toUpperCase();
    const benchmarkTicker = formData.benchmark_ticker
      ? formData.benchmark_ticker.trim().toUpperCase()
      : null;

    if (!mainTicker) {
      setErrorMessage("Укажите акцию для анализа.");
      return;
    }

    if (formData.horizons.length === 0) {
      setErrorMessage("Выберите хотя бы один горизонт анализа.");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");

      const payload = {
        main_ticker: mainTicker,
        direction: formData.direction,
        benchmark_ticker: benchmarkTicker,
        horizons: formData.horizons,
        only_official: true,
        include_events: formData.include_events,
        max_events: null,
      };

      const data = await analyzeKeyRateImpact(payload);

      setResult(data);
    } catch (error) {
      setErrorMessage(getAnalyzeErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  const mainTicker = formData.main_ticker.trim().toUpperCase() || "SBER";
  const companyName = COMPANY_NAMES[mainTicker] || mainTicker;
  const directionText = getDirectionText(formData.direction);
  const horizonText = formatSelectedHorizons(formData.horizons);

  return (
    <section className="card hypothesisSection">
      <div className="hypothesisHeader">
        <div>
          <p className="sectionKicker">Key Rate Impact</p>
          <h2>Анализ реакции на ставку</h2>
          <p>
            Показывает, как выбранная акция исторически реагировала на похожие
            решения по ключевой ставке.
          </p>
        </div>
      </div>

      <div className="hypothesisLayout">
        <form className="hypothesisForm" onSubmit={handleSubmit}>
          <div className="hypothesisGrid">
            <label className="hypothesisField wide">
              <span>Выбранная акция</span>
              <input
                value={formData.main_ticker}
                onChange={(event) =>
                  updateField("main_ticker", event.target.value.toUpperCase())
                }
                placeholder="Например: SBER"
              />
            </label>

            <label className="hypothesisField">
              <span>Сценарий решения ЦБ</span>
              <select
                value={formData.direction}
                onChange={(event) => updateField("direction", event.target.value)}
              >
                {DIRECTION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="hypothesisField">
              <span>Бенчмарк</span>
              <select
                value={formData.benchmark_ticker}
                onChange={(event) =>
                  updateField("benchmark_ticker", event.target.value)
                }
              >
                <option value="">Без бенчмарка</option>
                <option value="MOEX">MOEX</option>
              </select>
            </label>
          </div>

          <p className="hypothesisHint">
            Бенчмарк нужен только для относительного сравнения. Если не выбран,
            анализ показывает абсолютную реакцию акции.
          </p>

          <div className="hypothesisTickerChips">
            <span>Быстрый выбор акции:</span>
            {QUICK_TICKERS.map((item) => (
              <button
                className={mainTicker === item.secid ? "tickerChip active" : "tickerChip"}
                key={item.secid}
                type="button"
                title={item.name}
                onClick={() => selectMainTicker(item.secid)}
              >
                {item.secid}
              </button>
            ))}
          </div>

          <div className="hypothesisControlGroup">
            <span className="hypothesisControlLabel">Горизонты реакции</span>
            <div className="horizonSegment">
              {HORIZON_OPTIONS.map((option) => (
                <button
                  className={
                    formData.horizons.includes(option.value)
                      ? "horizonPill active"
                      : "horizonPill"
                  }
                  key={option.value}
                  type="button"
                  onClick={() => toggleHorizon(option.value)}
                >
                  {option.value}д
                </button>
              ))}
            </div>
            {formData.horizons.length === 0 && (
              <p className="inlineWarning">Выберите хотя бы один горизонт.</p>
            )}
          </div>

          <label className="hypothesisToggle">
            <input
              type="checkbox"
              checked={formData.include_events}
              onChange={(event) =>
                updateField("include_events", event.target.checked)
              }
            />
            <span className="toggleSwitch" aria-hidden="true" />
            <span>Показать исторические события</span>
          </label>

          <div className="hypothesisPreview">
            <span>Проверяемая гипотеза</span>
            <strong>
              {companyName} и сценарий:{" "}
              {DIRECTION_OPTIONS.find((item) => item.value === formData.direction)?.label}
            </strong>
            <p>
              Проверяем, как {companyName} исторически реагировал на{" "}
              {directionText} на горизонтах {horizonText}.
            </p>
          </div>

          {errorMessage && (
            <div className="error hypothesisError">
              <strong>Ошибка анализа</strong>
              <p>{errorMessage}</p>
            </div>
          )}

          <div className="hypothesisActions">
            <button
              className="primaryButton"
              type="submit"
              disabled={isLoading || formData.horizons.length === 0}
            >
              {isLoading
                ? "Анализируем..."
                : "Проанализировать"}
            </button>
          </div>
        </form>

        <HypothesisResultPanel result={result} isLoading={isLoading} />
      </div>
    </section>
  );
}

function getAnalyzeErrorMessage(error) {
  if (error?.status === 422) {
    return "Проверьте тикер и параметры анализа.";
  }

  if (
    error?.code === "key_rate_impact_market_data_unavailable" ||
    error?.status === 502
  ) {
    return "Не удалось получить свечи по выбранному тикеру.";
  }

  return error?.message || "Не удалось выполнить анализ.";
}

function getDirectionText(direction) {
  const labels = {
    rate_cut: "снижение ключевой ставки",
    rate_hike: "повышение ключевой ставки",
    rate_hold: "сохранение ключевой ставки",
  };

  return labels[direction] || "решения ЦБ по ключевой ставке";
}

function formatSelectedHorizons(horizons) {
  return horizons
    .slice()
    .sort((left, right) => left - right)
    .map((horizon) => `${horizon}`)
    .join(", ")
    .replace(/, ([^,]*)$/, " и $1")
    .concat(" торговых дней");
}
