import { apiRequest } from "../../shared/api/client.js";

export function refreshTickerPrice(secid) {
  return apiRequest(`/market/tickers/${secid}/refresh`, {
    method: "POST",
  });
}