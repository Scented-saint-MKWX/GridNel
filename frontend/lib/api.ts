import { getToken } from "@/lib/auth";
import { MOCK_MODE, mockDispatch } from "@/lib/mock/router";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class ForbiddenError extends ApiError {
  constructor() {
    super(403, "Forbidden — this account's role cannot access this resource.");
  }
}

export class UnauthorizedError extends ApiError {
  constructor() {
    super(401, "Unauthorized — session expired or invalid.");
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  // Dev-only mock branch, gated behind NEXT_PUBLIC_MOCK_MODE (never true in
  // .env.local.example). Same code path as the real fetch below with one
  // branch here — see lib/mock/router.ts. Delete this block, not a parallel
  // hook, when the backend lands.
  if (MOCK_MODE) {
    return mockDispatch<T>({ method: options.method ?? "GET", path, body: options.body });
  }

  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (res.status === 401) throw new UnauthorizedError();
  if (res.status === 403) throw new ForbiddenError();
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text || res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
