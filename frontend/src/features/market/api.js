import { apiRequest } from "../../shared/api/client.js";

export function refreshTickerPrice(secid) {
  return apiRequest(`/market/tickers/${secid}/refresh`, {
    method: "POST",
  });
}

export function getTickerPriceHistory(secid, limit = 50) {
  return apiRequest(
    `/market/tickers/${encodeURIComponent(secid)}/prices?limit=${limit}`
  );
}

export function getTickerCandles(secid, { interval = "1d", limit = 100 } = {}) {
  const params = new URLSearchParams({
    interval,
    limit: String(limit),
  });

  return apiRequest(
    `/market/tickers/${encodeURIComponent(secid)}/candles?${params.toString()}`
  );
}
