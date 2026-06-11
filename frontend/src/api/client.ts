import type { ApiError } from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly payload: ApiError,
  ) {
    super(payload.message);
    this.name = "ApiClientError";
  }
}

function fallbackError(status: number): ApiError {
  return {
    code: "unexpected_response",
    message: `服务返回了无法识别的响应（${status}）。`,
    trace_id: "unknown",
    details: {},
  };
}

export async function parseApiError(response: Response): Promise<ApiError> {
  try {
    return (await response.json()) as ApiError;
  } catch {
    return fallbackError(response.status);
  }
}

export async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiClientError(response.status, await parseApiError(response));
  }

  return (await response.json()) as T;
}
