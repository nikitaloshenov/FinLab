import { apiRequest } from "../../shared/api/client.js";

export function getWatchlist() {
  return apiRequest("/watchlist");
}

export function addWatchlistItem(secid) {
  return apiRequest("/watchlist/items", {
    method: "POST",
    body: JSON.stringify({
      secid,
    }),
  });
}

export function deleteWatchlistItem(secid) {
  return apiRequest(`/watchlist/items/${secid}`, {
    method: "DELETE",
  });
}

export function refreshWatchlistPrices() {
  return apiRequest("/watchlist/refresh-prices", {
    method: "POST",
  });
}