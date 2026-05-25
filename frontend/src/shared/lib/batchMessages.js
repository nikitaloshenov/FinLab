export function buildWatchlistRefreshMessage(result) {
  const message = `Обновлено тикеров: ${result.updated}/${result.total}. Ошибок: ${result.failed}.`;

  if (result.failed <= 0) {
    return message;
  }

  const failedItems = (result.items || [])
    .filter((item) => !item.success)
    .map((item) => `${item.secid}: ${item.error || "unknown error"}`);

  if (failedItems.length === 0) {
    return message;
  }

  return `${message} Не обновились: ${failedItems.join("; ")}.`;
}

export function buildAlertBatchCheckMessage(result) {
  const message = `Проверено alert’ов: ${result.checked}/${result.total}. Сработало: ${result.triggered}. Ошибок: ${result.failed}.`;

  if (result.failed <= 0) {
    return message;
  }

  const failedItems = (result.items || [])
    .filter((item) => !item.success)
    .map((item) => `#${item.alert_id}: ${item.error || "unknown error"}`);

  if (failedItems.length === 0) {
    return message;
  }

  return `${message} Ошибки: ${failedItems.join("; ")}.`;
}
