import { apiRequest } from "../../shared/api/client.js";

export function getAlerts() {
  return apiRequest("/alerts");
}

export function createAlert({ secid, condition, targetPrice }) {
  return apiRequest("/alerts", {
    method: "POST",
    body: JSON.stringify({
      secid,
      condition,
      target_price: targetPrice,
    }),
  });
}

export function checkAlert(alertId) {
  return apiRequest(`/alerts/${alertId}/check`, {
    method: "POST",
  });
}

export function deleteAlert(alertId) {
  return apiRequest(`/alerts/${alertId}`, {
    method: "DELETE",
  });
}

export function getAlertEvents() {
  return apiRequest("/alerts/events");
}