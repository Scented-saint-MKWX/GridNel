import type { JwtPayload } from "@/types/auth";

// In-memory only — never localStorage/sessionStorage/a JS-set cookie. See CLAUDE.md
// "Hard security rules". Module-level state is fine for a client-only auth token
// because it lives only for the tab's lifetime, same as React state would.
let currentToken: string | null = null;

export function setToken(token: string | null): void {
  currentToken = token;
}

export function getToken(): string | null {
  return currentToken;
}

export function decodeJwt(token: string): JwtPayload | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

export function isExpired(payload: JwtPayload | null): boolean {
  if (!payload) return true;
  return Date.now() >= payload.exp * 1000;
}
