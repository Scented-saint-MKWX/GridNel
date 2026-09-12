import {
  mockAlerts,
  mockCorridorSpeeds,
  mockDebugHash,
  mockDensity,
  mockHeatmap,
  mockLogin,
  mockOdFlows,
  mockTrajectory,
} from "@/lib/mock/fixtures";
import type { Role } from "@/types/auth";

export const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_MODE === "true";

// Demo credentials per CLAUDE.md "Definition of done" — mock mode must
// enforce the same username+password pairing the real /login would, not
// just guess a role from the username string (that let anyone escalate to
// tracker by typing any password with "track" in the username).
const DEMO_CREDENTIALS: Record<string, Role> = {
  tracker: "tracker",
  analyst: "analyst",
};
const DEMO_CREDENTIALS_PASSWORDS: Record<string, string> = {
  tracker: "track123",
  analyst: "analytics123",
};

interface MockRequest {
  method: "GET" | "POST" | "DELETE";
  path: string;
  body?: unknown;
}

// Single dispatch point for every mocked endpoint — mirrors the real /login,
// /track/*, /alerts, /analytics/*, /debug/hash paths exactly (TEAM.md §4.4)
// so lib/api.ts's real-vs-mock branch stays a one-line diff when the backend
// lands. Never invent a path or shape here that isn't in the frozen contract.
export async function mockDispatch<T>({ method, path, body }: MockRequest): Promise<T> {
  await new Promise((r) => setTimeout(r, 150 + Math.random() * 200));

  if (method === "POST" && path === "/login") {
    const { username, password } = (body ?? {}) as { username?: string; password?: string };
    const role = DEMO_CREDENTIALS[username ?? ""];
    if (!role || DEMO_CREDENTIALS_PASSWORDS[username ?? ""] !== password) {
      throw new Error("Invalid credentials.");
    }
    return mockLogin(role) as T;
  }

  const trackMatch = path.match(/^\/track\/([^/]+)(\/bridged)?$/);
  if (method === "GET" && trackMatch) {
    return mockTrajectory(decodeURIComponent(trackMatch[1]!)) as T;
  }

  const debugMatch = path.match(/^\/debug\/hash\/([^/]+)$/);
  if (method === "GET" && debugMatch) {
    return mockDebugHash(decodeURIComponent(debugMatch[1]!)) as T;
  }

  if (method === "GET" && path.startsWith("/alerts")) {
    const since = new URL(path, "http://mock").searchParams.get("since") ?? new Date(0).toISOString();
    return mockAlerts(since) as T;
  }

  if (method === "GET" && path.startsWith("/analytics/density")) {
    return mockDensity() as T;
  }
  if (method === "GET" && path.startsWith("/analytics/heatmap")) {
    return mockHeatmap() as T;
  }
  if (method === "GET" && path.startsWith("/analytics/corridor-speeds")) {
    return mockCorridorSpeeds() as T;
  }
  if (method === "GET" && path.startsWith("/analytics/od")) {
    return mockOdFlows() as T;
  }

  if (method === "POST" && path === "/blacklist") {
    return undefined as T;
  }

  const blacklistDeleteMatch = path.match(/^\/blacklist\/([^/]+)$/);
  if (method === "DELETE" && blacklistDeleteMatch) {
    return undefined as T;
  }

  throw new Error(`mock: no fixture wired for ${method} ${path}`);
}
