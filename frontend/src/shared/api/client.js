import { getDemoSessionId } from "../session.js";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "/api/v1"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details || {};
  }
}

export function isNetworkApiError(error) {
  return (
    error instanceof ApiError &&
    (error.status === 0 || error.code === "network_error")
  );
}

function parseErrorPayload(payload) {
  const fallback = {
    message: "API request failed",
    code: undefined,
    details: {},
  };

  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const { detail } = payload;

  if (typeof detail === "string") {
    return {
      ...fallback,
      message: detail,
    };
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((message) => typeof message === "string" && message.length > 0);

    return {
      ...fallback,
      message:
        messages.length > 0
          ? `Validation error: ${messages.join("; ")}`
          : "Validation error",
    };
  }

  if (detail && typeof detail === "object") {
    return {
      message:
        typeof detail.message === "string" && detail.message.length > 0
          ? detail.message
          : fallback.message,
      code: typeof detail.code === "string" ? detail.code : undefined,
      details:
        detail.details && typeof detail.details === "object"
          ? detail.details
          : {},
    };
  }

  return fallback;
}

async function parseErrorResponse(response) {
  const errorText = await response.text();

  if (!errorText) {
    return {
      message: "API request failed",
      code: undefined,
      details: {},
    };
  }

  try {
    return parseErrorPayload(JSON.parse(errorText));
  } catch {
    return {
      message: "API request failed",
      code: undefined,
      details: {},
    };
  }
}

export async function apiRequest(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        "X-FinLab-Session-Id": getDemoSessionId(),
        ...options.headers,
      },
      ...options,
    });
  } catch {
    throw new ApiError("Network request failed", {
      status: 0,
      code: "network_error",
    });
  }

  if (!response.ok) {
    const { message, code, details } = await parseErrorResponse(response);

    throw new ApiError(message, {
      status: response.status,
      code,
      details,
    });
  }

  return response.json();
}
