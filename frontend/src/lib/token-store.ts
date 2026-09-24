import type { TokenResponse } from "@/lib/types";

/**
 * The one place access/refresh tokens are read from and written to.
 *
 * A plain module, not a React hook, so `api.ts` (which isn't a component)
 * and `auth-context.tsx` (which is) can both use it without either
 * depending on the other. `auth-context.tsx` subscribes via
 * `subscribe()` to stay in sync with changes `api.ts` makes on its own
 * (a silent refresh, or clearing tokens after a failed refresh).
 */

const ACCESS_TOKEN_KEY = "learn_buddy.access_token";
const REFRESH_TOKEN_KEY = "learn_buddy.refresh_token";

type Listener = () => void;
const listeners = new Set<Listener>();

function notify(): void {
  for (const listener of listeners) listener();
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function readStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  return readStorage(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return readStorage(REFRESH_TOKEN_KEY);
}

export function setTokens(tokens: TokenResponse): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  } catch {
    // Private browsing / blocked storage: the session just won't persist
    // across a reload, which is a degraded experience, not a crash.
  }
  notify();
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // See setTokens.
  }
  notify();
}

/** Decode a JWT's payload without verifying it — the server already did that;
 * this only reads back claims (`sub`, `exp`) the UI needs. */
export function decodeJwtPayload<T>(token: string): T | null {
  try {
    const [, payload] = token.split(".");
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      "=",
    );
    return JSON.parse(atob(padded)) as T;
  } catch {
    return null;
  }
}
