import { apiRequest } from "../../shared/api/client.js";

export function getInstrumentReference(secid) {
  return apiRequest(`/reference/instruments/${encodeURIComponent(secid)}`);
}
