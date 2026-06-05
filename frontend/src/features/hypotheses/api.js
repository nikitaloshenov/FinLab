import { apiRequest } from "../../shared/api/client.js";

export function analyzeHypothesis(payload) {
  return apiRequest("/hypotheses/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function analyzeKeyRateImpact(payload) {
  return apiRequest("/hypotheses/key-rate-impact/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

