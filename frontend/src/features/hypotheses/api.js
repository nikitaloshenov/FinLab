import { apiRequest } from "../../shared/api/client.js";

export function analyzeHypothesis(payload) {
  return apiRequest("/hypotheses/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

