import { apiRequest } from "../../shared/api/client.js";

export function getWatchlist() {
  return apiRequest("/watchlist");
}