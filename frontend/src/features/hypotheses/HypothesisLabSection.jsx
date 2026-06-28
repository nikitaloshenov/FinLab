import { useEffect, useState } from "react";

import { analyzeKeyRateImpactV2 } from "./api.js";
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

const EVENT_DIRECTION_OPTIONS = [
  { value: "all", label: "Все решения", preview: "после решений ЦБ" },
  { value: "hike", label: "Повышение ставки", preview: "после повышений ставки" },
  { value: "cut", label: "Снижение ставки", preview: "после снижений ставки" },
  { value: "hold", label: "Без изменений", preview: "после сохранения ставки" },
];

const HORIZON_OPTIONS = [
  { value: 1, label: "1 торговый день" },
  { value: 5, label: "5 торговых дней" },
  { value: 10, label: "10 торговых дней" },
];

const CURRENT_YEAR = new Date().getFullYear();
const CURRENT_DATE = new Date().toISOString().slice(0, 10);
const YEAR_OPTIONS = Array.from(
  { length: Math.max(CURRENT_YEAR, 2026) - 2020 + 1 },
  (_, index) => 2020 + index,
);

const DEFAULT_FORM = {
  main_ticker: "SBER",
  event_direction: "all",
  period_start_year: 2024,
  period_end_year: CURRENT_YEAR,
  use_custom_dates: false,
  date_from: "2024-01-01",
  date_to: CURRENT_YEAR === new Date(CURRENT_DATE).getFullYear() ? CURRENT_DATE : `${CURRENT_YEAR}-12-31`,
  horizons: [1, 5, 10],
  auto_prepare_data: true,
  refresh_candles: false,
  include_sector_comparison: true,
  sector_peer_limit: 8,
  auto_prepare_sector_data: false,
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
    const peerLimit = Number(formData.sector_peer_limit) || 8;
    const selectedDateRange = getSelectedDateRange(formData);

    if (!mainTicker) {
      setErrorMessage("Укажите акцию для анализа.");
      return;
    }

    if (formData.horizons.length === 0) {
      setErrorMessage("Выберите хотя бы один горизонт анализа.");
      return;
    }

    if (
      selectedDateRange.date_from &&
      selectedDateRange.date_to &&
      selectedDateRange.date_from > selectedDateRange.date_to
    ) {
      setErrorMessage("Дата начала должна быть раньше даты окончания.");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage("");

      const payload = {
        secid: mainTicker,
        event_direction: formData.event_direction,
        date_from: selectedDateRange.date_from || null,
        date_to: selectedDateRange.date_to || null,
        horizons: formData.horizons,
        auto_prepare_data: formData.auto_prepare_data,
        refresh_candles: formData.refresh_candles,
        include_sector_comparison: formData.include_sector_comparison,
        sector_peer_limit: Math.min(Math.max(peerLimit, 1), 15),
        auto_prepare_sector_data: formData.auto_prepare_sector_data,
      };

      const data = await analyzeKeyRateImpactV2(payload);

      setResult(data);
    } catch (error) {
      setErrorMessage(getAnalyzeErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  const mainTicker = formData.main_ticker.trim().toUpperCase() || "SBER";
  const companyName = COMPANY_NAMES[mainTicker] || mainTicker;
  const horizonText = formatSelectedHorizons(formData.horizons);
  const directionOption =
    EVENT_DIRECTION_OPTIONS.find((option) => option.value === formData.event_direction) ||
    EVENT_DIRECTION_OPTIONS[0];
  const selectedDateRange = getSelectedDateRange(formData);
  const usesCurrentYear = Number(formData.period_end_year) === CURRENT_YEAR;

  return (
    <section className="card hypothesisSection">
      <div className="hypothesisHeader">
        <div>
          <p className="sectionKicker">Key Rate Impact v2</p>
          <h2>Анализ реакции на решения ЦБ</h2>
          <p>
            Исторический event-study по дневным свечам: выбранная акция, решения по
            ключевой ставке, торговые горизонты и сравнение с компаниями сектора.
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

            <label className="hypothesisField wide">
              <span>Тип решения ЦБ</span>
              <select
                value={formData.event_direction}
                onChange={(event) => updateField("event_direction", event.target.value)}
              >
                {EVENT_DIRECTION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="datePeriodGroup">
            <span className="hypothesisControlLabel">Период решений ЦБ</span>
            <div className="hypothesisGrid">
              <label className="hypothesisField">
                <span>С года</span>
                <select
                  value={formData.period_start_year}
                  onChange={(event) => {
                    const startYear = Number(event.target.value);
                    setFormData((currentFormData) => ({
                      ...currentFormData,
                      period_start_year: startYear,
                      period_end_year: Math.max(startYear, Number(currentFormData.period_end_year)),
                      use_custom_dates: false,
                    }));
                  }}
                >
                  {YEAR_OPTIONS.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </label>

              <label className="hypothesisField">
                <span>По год</span>
                <select
                  value={formData.period_end_year}
                  onChange={(event) => {
                    const endYear = Number(event.target.value);
                    setFormData((currentFormData) => ({
                      ...currentFormData,
                      period_start_year: Math.min(Number(currentFormData.period_start_year), endYear),
                      period_end_year: endYear,
                      use_custom_dates: false,
                    }));
                  }}
                >
                  {YEAR_OPTIONS.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="hypothesisHint">
              Мы берём решения ЦБ внутри выбранных лет и считаем реакцию акции после
              каждого события. Диапазон запроса: {selectedDateRange.date_from} —{" "}
              {selectedDateRange.date_to}.
            </p>
            {usesCurrentYear && !formData.use_custom_dates && (
              <p className="hypothesisHint">
                Для выбранных горизонтов нужны дневные цены после даты решения ЦБ.
                Самые свежие события могут быть пропущены, если последующих свечей ещё
                недостаточно.
              </p>
            )}
          </div>

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
            <div className="horizonSegment v2">
              {HORIZON_OPTIONS.map((option) => (
                <button
                  className={
                    formData.horizons.includes(option.value)
                      ? "horizonPill active"
                      : "horizonPill"
                  }
                  key={option.value}
                  type="button"
                  title={option.label}
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
              checked={formData.include_sector_comparison}
              onChange={(event) =>
                updateField("include_sector_comparison", event.target.checked)
              }
            />
            <span className="toggleSwitch" aria-hidden="true" />
            <span>Сравнить с компаниями того же сектора</span>
          </label>

          <details className="advancedSettings">
            <summary>Дополнительные настройки</summary>
            <div className="advancedSettingsBody">
              <label className="hypothesisToggle compact">
                <input
                  type="checkbox"
                  checked={formData.auto_prepare_data}
                  onChange={(event) =>
                    updateField("auto_prepare_data", event.target.checked)
                  }
                />
                <span className="toggleSwitch" aria-hidden="true" />
                <span>Подготовить недостающие события и дневные цены</span>
              </label>

              <label className="hypothesisToggle compact">
                <input
                  type="checkbox"
                  checked={formData.refresh_candles}
                  onChange={(event) =>
                    updateField("refresh_candles", event.target.checked)
                  }
                />
                <span className="toggleSwitch" aria-hidden="true" />
                <span>Перезагрузить дневные свечи акции</span>
              </label>

              {formData.include_sector_comparison && (
                <>
                  <label className="hypothesisField">
                    <span>Количество компаний для сравнения</span>
                    <input
                      type="number"
                      min="1"
                      max="15"
                      value={formData.sector_peer_limit}
                      onChange={(event) =>
                        updateField("sector_peer_limit", event.target.value)
                      }
                    />
                  </label>
                  <label className="hypothesisToggle compact">
                    <input
                      type="checkbox"
                      checked={formData.auto_prepare_sector_data}
                      onChange={(event) =>
                        updateField("auto_prepare_sector_data", event.target.checked)
                      }
                    />
                    <span className="toggleSwitch" aria-hidden="true" />
                    <span>Догрузить дневные цены компаний сектора</span>
                  </label>
                  <p className="hypothesisHint">
                    По умолчанию данные компаний сектора не догружаются, чтобы не делать
                    неожиданных запросов к MOEX.
                  </p>
                </>
              )}
              <details className="customDateDetails">
                <summary>Указать даты вручную</summary>
                <div className="hypothesisGrid">
                  <label className="hypothesisField">
                    <span>Дата с</span>
                    <input
                      type="date"
                      value={formData.date_from}
                      onChange={(event) => {
                        updateField("date_from", event.target.value);
                        updateField("use_custom_dates", true);
                      }}
                    />
                  </label>

                  <label className="hypothesisField">
                    <span>Дата по</span>
                    <input
                      type="date"
                      value={formData.date_to}
                      onChange={(event) => {
                        updateField("date_to", event.target.value);
                        updateField("use_custom_dates", true);
                      }}
                    />
                  </label>
                </div>
                <label className="hypothesisToggle compact">
                  <input
                    type="checkbox"
                    checked={formData.use_custom_dates}
                    onChange={(event) =>
                      updateField("use_custom_dates", event.target.checked)
                    }
                  />
                  <span className="toggleSwitch" aria-hidden="true" />
                  <span>Использовать ручной диапазон дат</span>
                </label>
              </details>
            </div>
          </details>

          <div className="hypothesisPreview">
            <span>Что проверяем</span>
            <strong>
              {companyName} {directionOption.preview}
            </strong>
            <p>
              Анализируем историческую реакцию на горизонтах {horizonText}. Сравнение с
              компаниями сектора не является формальным секторным индексом.
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
              {isLoading ? "Анализируем..." : "Запустить анализ"}
            </button>
          </div>
        </form>

        <HypothesisResultPanel result={result} isLoading={isLoading} />
      </div>
    </section>
  );
}

function getSelectedDateRange(formData) {
  if (formData.use_custom_dates) {
    return {
      date_from: formData.date_from,
      date_to: formData.date_to,
    };
  }

  const startYear = Number(formData.period_start_year) || 2024;
  const endYear = Number(formData.period_end_year) || CURRENT_YEAR;

  return {
    date_from: `${startYear}-01-01`,
    date_to: endYear === CURRENT_YEAR ? CURRENT_DATE : `${endYear}-12-31`,
  };
}

function getAnalyzeErrorMessage(error) {
  if (error?.status === 422) {
    return "Проверьте ticker, даты и параметры анализа.";
  }

  if (error?.code === "key_rate_v2_unknown_instrument" || error?.status === 404) {
    return "Инструмент не найден в reference layer. Проверьте ticker.";
  }

  if (error?.code === "key_rate_v2_data_not_prepared" || error?.status === 409) {
    return "Нет подготовленных событий или дневных цен. Включите подготовку данных и повторите анализ.";
  }

  if (error?.code === "key_rate_v2_data_preparation_failed" || error?.status === 502) {
    return "Не удалось подготовить дневные свечи. Проверьте доступность MOEX/API и повторите позже.";
  }

  if (error?.code === "network_error" || error?.status === 0) {
    return "Не удалось подключиться к API. Проверьте, что backend запущен.";
  }

  return error?.message || "Не удалось выполнить анализ.";
}

function formatSelectedHorizons(horizons) {
  const sortedHorizons = horizons.slice().sort((left, right) => left - right);

  if (sortedHorizons.length === 0) {
    return "не выбраны";
  }

  return sortedHorizons
    .map((horizon) => `${horizon}`)
    .join(", ")
    .replace(/, ([^,]*)$/, " и $1")
    .concat(" торговых дней");
}
