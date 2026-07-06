export function HypothesisResultPanel({ result, isLoading }) {
  if (isLoading && !result) {
    return (
      <div className="hypothesisResult">
        <div className="emptyState hypothesisPlaceholder">
          <strong>Запускаем анализ...</strong>
          <p>
            Проверяем решения ЦБ, цены и при необходимости готовим недостающие данные
            для выбранной акции.
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="hypothesisResult">
        <div className="emptyState hypothesisPlaceholder">
          <strong>Выберите акцию и период решений ЦБ</strong>
          <p>
            После запуска FinLab покажет среднюю реакцию акции после решений ЦБ,
            лучший горизонт, долю положительных реакций и сравнение с компаниями
            сектора.
          </p>
          <ul className="previewList">
            <li>Итоговый вывод</li>
            <li>Реакция по горизонтам</li>
            <li>Сравнение с компаниями сектора</li>
            <li>Качество данных</li>
          </ul>
        </div>
      </div>
    );
  }

  if (isV2Result(result)) {
    return <KeyRateV2Result result={result} />;
  }

  return <LegacyResultFallback result={result} />;
}

function KeyRateV2Result({ result }) {
  return (
    <div className="hypothesisResult">
      <V2VerdictCard result={result} />
      <KpiRow result={result} />
      <V2HorizonSummaryTable items={result.summary || []} />
      <SectorComparisonBlock sectorComparison={result.sector_comparison} />
      <DataPreparationBlock dataPreparation={result.data_preparation} />
      <EventsBlock events={result.events} fallbackItems={result.sample_results || []} />
      <MethodologyNote />
    </div>
  );
}

function V2VerdictCard({ result }) {
  const instrumentName = result.instrument?.name || result.secid;
  const directionText = getDirectionTitle(result.event_direction);
  const bestHorizon = findBestHorizon(result.summary || []);
  const oneDay = findHorizon(result.summary || [], 1);
  const title = `${instrumentName} ${directionText.titleSuffix}`;
  const badge = getReactionBadge(bestHorizon);

  return (
    <section className="assessmentCard">
      <span className={`assessmentBadge ${badge.tone}`}>{badge.label}</span>
      <h3>{title}</h3>
      <p>
        {buildVerdictText({
          result,
          bestHorizon,
          oneDay,
          directionText,
        })}
      </p>
      <p className="resultHint">
        Это историческое наблюдение, а не прогноз и не инвестиционная рекомендация.
      </p>
    </section>
  );
}

function KpiRow({ result }) {
  const bestHorizon = findBestHorizon(result.summary || []);
  const sectorKpi = getSectorKpi(result.sector_comparison);

  return (
    <section className="resultMetricsGrid kpiGrid">
      <Metric
        label="Использовано событий"
        value={`${result.events_processed} из ${result.events_total}`}
      />
      <Metric
        label="Лучший горизонт"
        value={bestHorizon ? formatTradingDays(bestHorizon.horizon_trading_days) : "—"}
      />
      <Metric
        label="Средняя реакция"
        value={formatPercent(bestHorizon?.average_return_percent)}
        tone={getTone(bestHorizon?.average_return_percent)}
      />
      <Metric
        label="Доля положительных"
        value={formatPercent(bestHorizon?.hit_rate_percent)}
      />
      <Metric
        label="Сравнение с сектором"
        value={sectorKpi.value}
        tone={sectorKpi.tone}
      />
    </section>
  );
}

function V2HorizonSummaryTable({ items }) {
  return (
    <section className="resultBlock horizonTableBlock">
      <div className="resultBlockHeader">
        <h3>Реакция по горизонтам</h3>
      </div>
      {items.length === 0 ? (
        <p className="resultHint">Нет данных для таблицы горизонтов.</p>
      ) : (
        <div className="tableWrapper compactTable horizonSummaryTable">
          <table>
            <thead>
              <tr>
                <th>Горизонт</th>
                <th>Средняя</th>
                <th>Медиана</th>
                <th>Рост</th>
                <th>Доля роста</th>
                <th>Событий</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  className={item.best_horizon_flag ? "highlightDataRow" : undefined}
                  key={item.horizon_trading_days}
                >
                  <td>
                    {item.horizon_trading_days}д
                    {item.best_horizon_flag && (
                      <span className="tableSubtext">лучший средний результат</span>
                    )}
                  </td>
                  <td className={getTone(item.average_return_percent)}>
                    {formatPercent(item.average_return_percent)}
                  </td>
                  <td className={getTone(item.median_return_percent)}>
                    {formatPercent(item.median_return_percent)}
                  </td>
                  <td>
                    {item.positive_count}
                    <span className="tableSubtext">
                      падение: {item.negative_count}, без изменений: {item.neutral_count}
                    </span>
                  </td>
                  <td>{formatPercent(item.hit_rate_percent)}</td>
                  <td>
                    {item.sample_size}
                    <span className="tableSubtext">пропущено: {item.skipped_count}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SectorComparisonBlock({ sectorComparison }) {
  if (!sectorComparison) {
    return null;
  }

  if (sectorComparison.status === "disabled") {
    return (
      <section className="resultBlock secondaryResultBlock quietResultBlock">
        <p className="resultHint">Сравнение с компаниями сектора отключено.</p>
      </section>
    );
  }

  return (
    <section className="resultBlock secondaryResultBlock">
      <div className="resultBlockHeader">
        <h3>Сравнение с компаниями сектора</h3>
        <span>{formatSectorStatus(sectorComparison.status)}</span>
      </div>

      {sectorComparison.status === "success" ? (
        <>
          <SectorInsight sectorComparison={sectorComparison} />
          <PeerList peerSecids={sectorComparison.peer_secids || []} />
          <SectorSummaryTable items={sectorComparison.summary || []} />
        </>
      ) : (
        <SectorEmptyState sectorComparison={sectorComparison} />
      )}

      <SkippedPeers peers={sectorComparison.peers_skipped || []} />
    </section>
  );
}

function SectorInsight({ sectorComparison }) {
  const best = findBestSectorSummary(sectorComparison.summary || []);
  const sectorName = formatSectorName(
    sectorComparison.sector?.name || sectorComparison.sector?.code || "сектор",
  );

  if (!best || best.excess_return_percent === null || best.excess_return_percent === undefined) {
    return (
      <p className="resultHint">
        Сектор: {sectorName}. Использовано компаний сектора: {sectorComparison.peers_used} из{" "}
        {sectorComparison.peers_total}.
      </p>
    );
  }

  const excess = Number(best.excess_return_percent);
  const relation = excess >= 0 ? "лучше" : "хуже";
  const verdict =
    excess >= 0
      ? `Опережение сектора: ${formatSignedPercentagePoints(best.excess_return_percent)}`
      : `Отставание от сектора: ${formatSignedPercentagePoints(best.excess_return_percent)}`;

  return (
    <div className="sectorCallout">
      <span>{verdict}</span>
      <strong>
        На горизонте {best.horizon_trading_days}д акция была {relation} среднего по
        сектору на {formatSignedPercentagePoints(excess)}
      </strong>
      <p>
        Сектор: {sectorName}. Использовано компаний сектора: {sectorComparison.peers_used} из{" "}
        {sectorComparison.peers_total}.
      </p>
    </div>
  );
}

function SectorSummaryTable({ items }) {
  if (items.length === 0) {
    return <p className="resultHint">Нет расчетных строк по сектору.</p>;
  }

  return (
    <div className="tableWrapper compactTable sectorSummaryTable">
      <table>
        <thead>
          <tr>
            <th>Горизонт</th>
            <th>Акция</th>
            <th>Сектор</th>
            <th>Разница</th>
            <th>Компаний</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.horizon_trading_days}>
              <td>{item.horizon_trading_days}д</td>
              <td className={getTone(item.selected_average_return_percent)}>
                {formatPercent(item.selected_average_return_percent)}
              </td>
              <td className={getTone(item.sector_average_return_percent)}>
                {formatPercent(item.sector_average_return_percent)}
                <span className="tableSubtext">
                  медиана: {formatPercent(item.sector_median_return_percent)}
                </span>
              </td>
              <td className={getTone(item.excess_return_percent)}>
                {formatPercent(item.excess_return_percent)}
              </td>
              <td>
                {item.sector_instrument_count || "—"}
                <span className="tableSubtext">
                  доля +: {formatPercent(item.sector_hit_rate_percent)}
                </span>
                {item.selected_rank_in_sector && (
                  <span className="tableSubtext">
                    позиция: {item.selected_rank_in_sector}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectorEmptyState({ sectorComparison }) {
  const messages = {
    insufficient_data:
      "Сектор найден, но по компаниям сектора пока не хватает дневных цен для сравнения. Можно включить догрузку данных компаний сектора в дополнительных настройках.",
    no_sector_mapping:
      "Для этой акции сектор пока не указан в справочнике FinLab, поэтому сравнение с компаниями сектора недоступно.",
    no_peers: "Для этого сектора пока не найдено подходящих компаний для сравнения.",
  };

  return (
    <p className="resultHint">
      {messages[sectorComparison.status] || "Сравнение с компаниями сектора недоступно."}
    </p>
  );
}

function PeerList({ peerSecids }) {
  if (peerSecids.length === 0) {
    return null;
  }

  return (
    <div className="peerChipList" aria-label="Компании сектора">
      {peerSecids.map((secid) => (
        <span className="peerChip" key={secid}>
          {secid}
        </span>
      ))}
    </div>
  );
}

function SkippedPeers({ peers }) {
  if (peers.length === 0) {
    return null;
  }

  return (
    <details className="eventDetails compactDetails">
      <summary>Пропущенные компании сектора</summary>
      <ul className="limitationList detailsList">
        {peers.map((peer) => (
          <li key={`${peer.secid}-${peer.reason}`}>
            {peer.secid}: {formatPeerSkipReason(peer.reason)}
          </li>
        ))}
      </ul>
    </details>
  );
}

function DataPreparationBlock({ dataPreparation }) {
  if (!dataPreparation) {
    return null;
  }

  const preparedText =
    dataPreparation.key_rate_events_importer_ran || dataPreparation.candles_importer_ran
      ? "Часть данных была подготовлена во время анализа."
      : "Данные доступны для анализа.";

  return (
    <section className="resultBlock secondaryResultBlock quietResultBlock">
      <details className="eventDetails">
        <summary>Качество данных</summary>
        <div className="detailsBody">
          <p className="resultHint">{preparedText}</p>
          <div className="resultMetricsGrid compact">
            <Metric
              label="События готовы"
              value={formatBoolean(dataPreparation.key_rate_events_ready)}
            />
            <Metric
              label="События обновлены"
              value={formatBoolean(dataPreparation.key_rate_events_importer_ran)}
            />
            <Metric
              label="Цены готовы"
              value={formatBoolean(dataPreparation.candles_ready)}
            />
            <Metric
              label="Цены обновлены"
              value={formatBoolean(dataPreparation.candles_importer_ran)}
            />
            <Metric label="Загружено записей" value={dataPreparation.candles_rows_loaded} />
            <Metric
              label="Период доступных цен"
              value={`${dataPreparation.required_from || "—"} — ${
                dataPreparation.required_to || "—"
              }`}
            />
          </div>
          <p className="resultHint">
            Период цен может быть шире выбранного периода решений ЦБ: для расчёта нужны
            данные после даты последнего события.
          </p>
          <p className="resultHint">
            Для расчёта нужны цены после даты решения ЦБ. Самые свежие события могут
            быть пропущены, если последующих торговых данных ещё недостаточно.
          </p>
        </div>
      </details>
    </section>
  );
}

function EventsBlock({ events, fallbackItems }) {
  if (!events && fallbackItems.length === 0) {
    return null;
  }

  if (!events) {
    const groupedEvents = groupSampleResults(fallbackItems);

    return (
      <section className="resultBlock secondaryResultBlock quietResultBlock">
        <details className="eventDetails">
          <summary>Примеры рассчитанных событий</summary>
          <div className="eventDetailsList">
            {groupedEvents.map((event) => (
              <CalculatedEventCard event={event} key={event.key} />
            ))}
          </div>
          <p className="resultHint">
            Показана часть рассчитанных событий из ответа API. Полный список событий в
            этом ответе недоступен.
          </p>
        </details>
      </section>
    );
  }

  return (
    <section className="resultBlock secondaryResultBlock quietResultBlock">
      <details className="eventDetails">
        <summary>Решения ЦБ в расчёте</summary>
        <div className="eventDetailsList">
          {(events.used || []).map((event) => (
            <CalculatedEventCard event={normalizeApiEvent(event)} key={event.event_id} />
          ))}
        </div>
        <p className="resultHint">
          Использовано {events.used_total} из {events.found_total} найденных решений ЦБ.
        </p>
      </details>
      {(events.skipped || []).length > 0 && (
        <details className="eventDetails compactDetails">
          <summary>Пропущенные решения ЦБ</summary>
          <div className="eventDetailsList">
            {events.skipped.map((event) => (
              <article key={event.event_id}>
                <strong>{formatEventTitle(event)}</strong>
                <p>Пропущено: {formatSkipReason(event.reason)}</p>
              </article>
            ))}
          </div>
          <p className="resultHint">
            Часть свежих событий может быть пропущена, если для выбранных горизонтов ещё
            нет последующих цен.
          </p>
        </details>
      )}
    </section>
  );
}

function CalculatedEventCard({ event }) {
  return (
    <article>
      <strong>{event.title}</strong>
      <div className="eventReturnGrid">
        {event.horizons.map((item) => (
          <span
            className={getTone(item.return_percent)}
            key={`${event.key}-${item.horizon_trading_days}`}
          >
            {item.horizon_trading_days}д:{" "}
            {item.status === "success"
              ? formatPercent(item.return_percent)
              : formatSkipReason(item.skipped_reason)}
          </span>
        ))}
      </div>
    </article>
  );
}

function MethodologyNote() {
  return (
    <section className="resultBlock secondaryResultBlock quietResultBlock">
      <p className="resultHint">
        Как читать результат: анализ берёт первую доступную цену акции на дату решения
        ЦБ или после неё, затем сравнивает цену через выбранное число торговых дней.
        Сравнение с компаниями сектора показывает среднюю реакцию похожих компаний, а
        не официальный индекс.
      </p>
    </section>
  );
}

function LegacyResultFallback({ result }) {
  return (
    <div className="hypothesisResult">
      <section className="assessmentCard">
        <span className="assessmentBadge neutral">Старый формат ответа</span>
        <h3>{result?.summary?.company_name || result?.main_ticker || "Key Rate Analyzer"}</h3>
        <p>
          Получен ответ в старом формате. Обновите страницу и запустите анализ ещё раз.
        </p>
      </section>
    </div>
  );
}

function Metric({ label, value, tone }) {
  const className = tone ? `resultMetric ${tone}` : "resultMetric";

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function buildVerdictText({ result, bestHorizon, oneDay, directionText }) {
  const eventsInfo = result.events;
  const foundTotal = eventsInfo?.found_total ?? result.events_total;
  const usedTotal = eventsInfo?.used_total ?? result.events_processed;
  const skippedTotal = eventsInfo?.skipped_total ?? result.events_skipped;
  const eventsText = `За выбранный период найдено ${foundTotal} ${pluralizeEvent(
    foundTotal,
  )}.`;
  const processedText =
    skippedTotal > 0
      ? ` В расчёте использовано ${usedTotal}, пропущено ${skippedTotal} из-за нехватки цен для выбранных горизонтов.`
      : " Все найденные решения использованы в расчёте.";

  if (!bestHorizon) {
    return `${eventsText}${processedText} По выбранным горизонтам пока недостаточно данных для устойчивого вывода.`;
  }

  const oneDayText = oneDay
    ? ` На следующий торговый день средняя реакция составила ${formatPercent(
        oneDay.average_return_percent,
      )}.`
    : "";

  return `${eventsText}${processedText} ${directionText.sentencePrefix} лучший средний результат был на горизонте ${formatTradingDays(bestHorizon.horizon_trading_days)}: ${formatPercent(bestHorizon.average_return_percent)}.${oneDayText}`;
}

function getReactionBadge(bestHorizon) {
  if (!bestHorizon || !bestHorizon.sample_size || bestHorizon.sample_size < 2) {
    return { label: "Мало данных", tone: "insufficient_data" };
  }

  const average = Number(bestHorizon.average_return_percent);
  const hitRate = Number(bestHorizon.hit_rate_percent);

  if (Number.isNaN(average)) {
    return { label: "Смешанная реакция", tone: "neutral" };
  }

  if (average > 0.1 && hitRate >= 50) {
    return { label: "Чаще рост", tone: "positive" };
  }

  if (average < -0.1) {
    return { label: "Чаще снижение", tone: "negative" };
  }

  return { label: "Смешанная реакция", tone: "neutral" };
}

function getSectorKpi(sectorComparison) {
  if (!sectorComparison) {
    return { value: "—" };
  }

  if (sectorComparison.status === "disabled") {
    return { value: "Отключено" };
  }

  if (sectorComparison.status === "no_sector_mapping") {
    return { value: "Сектор не найден" };
  }

  if (sectorComparison.status === "insufficient_data") {
    return { value: "Недостаточно данных" };
  }

  if (sectorComparison.status === "no_peers") {
    return { value: "Нет компаний" };
  }

  const best = findBestSectorSummary(sectorComparison.summary || []);
  if (!best || best.excess_return_percent === null || best.excess_return_percent === undefined) {
    return { value: "Нет расчёта" };
  }

  const excess = Number(best.excess_return_percent);
  return {
    value:
      excess >= 0
        ? `Лучше на ${formatSignedPercentagePoints(best.excess_return_percent)}`
        : `Хуже на ${formatSignedPercentagePoints(best.excess_return_percent)}`,
    tone: excess >= 0 ? "positive" : "negative",
  };
}

function findBestHorizon(items) {
  return (
    items.find((item) => item.best_horizon_flag) ||
    items
      .filter((item) => item.average_return_percent !== null && item.average_return_percent !== undefined)
      .sort(
        (left, right) =>
          Number(right.average_return_percent) - Number(left.average_return_percent),
      )[0]
  );
}

function findHorizon(items, horizon) {
  return items.find((item) => item.horizon_trading_days === horizon);
}

function findBestSectorSummary(items) {
  return items
    .filter((item) => item.excess_return_percent !== null && item.excess_return_percent !== undefined)
    .sort(
      (left, right) =>
        Math.abs(Number(right.excess_return_percent)) -
        Math.abs(Number(left.excess_return_percent)),
    )[0];
}

function getDirectionTitle(value) {
  const labels = {
    hike: {
      titleSuffix: "после повышений ключевой ставки",
      sentencePrefix: "После повышений ключевой ставки",
    },
    cut: {
      titleSuffix: "после снижений ключевой ставки",
      sentencePrefix: "После снижений ключевой ставки",
    },
    hold: {
      titleSuffix: "после сохранения ключевой ставки",
      sentencePrefix: "После сохранения ставки без изменений",
    },
    all: {
      titleSuffix: "после решений ЦБ",
      sentencePrefix: "По всем решениям ЦБ",
    },
  };

  return labels[value] || labels.all;
}

function pluralizeEvent(count) {
  const normalizedCount = Math.abs(Number(count)) % 100;
  const lastDigit = normalizedCount % 10;

  if (normalizedCount > 10 && normalizedCount < 20) {
    return "решений ЦБ";
  }

  if (lastDigit === 1) {
    return "решение ЦБ";
  }

  if (lastDigit >= 2 && lastDigit <= 4) {
    return "решения ЦБ";
  }

  return "решений ЦБ";
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

function groupSampleResults(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = item.event_date || `event-${item.event_id}`;
    const existing = grouped.get(key) || {
      key,
      eventId: item.event_id,
      hasTechnicalFallback: !item.event_date,
      title: item.event_date
        ? `Решение ЦБ от ${formatDate(item.event_date)}`
        : "Решение ЦБ",
      horizons: [],
    };

    existing.horizons.push(item);
    grouped.set(key, existing);
  }

  return Array.from(grouped.values())
    .map((event) => ({
      ...event,
      horizons: event.horizons
        .slice()
        .sort((left, right) => left.horizon_trading_days - right.horizon_trading_days),
    }))
    .slice(0, 5);
}

function normalizeApiEvent(event) {
  return {
    key: `event-${event.event_id}`,
    eventId: event.event_id,
    hasTechnicalFallback: !event.event_date,
    title: formatEventTitle(event),
    horizons: (event.horizons || [])
      .slice()
      .sort((left, right) => left.horizon_trading_days - right.horizon_trading_days),
  };
}

function formatEventTitle(event) {
  const dateText = event.event_date ? formatDate(event.event_date) : `#${event.event_id}`;
  const directionText = formatEventDirection(event.direction);

  return directionText
    ? `${dateText} — ${directionText}`
    : `Решение ЦБ от ${dateText}`;
}

function formatEventDirection(value) {
  const labels = {
    hike: "повышение ставки",
    cut: "снижение ставки",
    hold: "без изменений",
    rate_hike: "повышение ставки",
    rate_cut: "снижение ставки",
    rate_hold: "без изменений",
  };

  return labels[value] || "";
}

function formatSectorName(value) {
  const labels = {
    Finance: "Финансы",
    finance: "Финансы",
    Banks: "Банки",
    banks: "Банки",
    "Oil & Gas": "Нефтегаз",
    OilGas: "Нефтегаз",
    oil_gas: "Нефтегаз",
    Technology: "Технологии",
    technology: "Технологии",
    Transport: "Транспорт",
    transport: "Транспорт",
  };

  return labels[value] || value;
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return value;
  }

  const prefix = numberValue > 0 ? "+" : "";

  return `${prefix}${new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numberValue)}%`;
}

function formatTradingDays(value) {
  const numberValue = Number(value);

  if (numberValue === 1) {
    return "1 торговый день";
  }

  return `${numberValue} торговых дней`;
}

function formatSignedPercentagePoints(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return value;
  }

  return `${new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(numberValue))} п.п.`;
}

function formatBoolean(value) {
  return value ? "Да" : "Нет";
}

function formatSectorStatus(value) {
  const labels = {
    success: "готово",
    disabled: "отключено",
    no_sector_mapping: "сектор не найден",
    no_peers: "нет компаний",
    insufficient_data: "недостаточно данных",
  };

  return labels[value] || value || "—";
}

function formatPeerSkipReason(value) {
  const labels = {
    missing_daily_candles: "нет дневных цен",
    insufficient_event_data: "недостаточно событий с данными",
    candle_import_failed: "не удалось загрузить цены",
  };

  return labels[value] || value || "причина не определена";
}

function formatSkipReason(value) {
  const labels = {
    no_event_candle: "нет дневных цен в базе за этот период",
    invalid_event_price: "некорректная цена на дату решения",
    no_horizon_candles:
      "не хватило цен после даты решения для выбранного горизонта",
    invalid_horizon_price: "некорректная цена на горизонте",
    no_events_found: "события не найдены",
  };

  return labels[value] || value || "причина не определена";
}

function getTone(value) {
  const numberValue = Number(value);

  if (Number.isNaN(numberValue) || numberValue === 0) {
    return undefined;
  }

  return numberValue > 0 ? "positive" : "negative";
}

function isV2Result(result) {
  return Boolean(result?.data_preparation && Array.isArray(result?.summary));
}
