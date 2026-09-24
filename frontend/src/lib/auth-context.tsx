"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api";
import {
  clearTokens,
  decodeJwtPayload,
  getAccessToken,
  getRefreshToken,
  setTokens,
  subscribe,
} from "@/lib/token-store";
import type { TokenResponse } from "@/lib/types";

interface AccessTokenClaims {
  sub: string;
}

interface AuthContextValue {
  studentId: string | null;
  isAuthenticated: boolean;
  /** True until the first read of stored tokens completes (client-only, avoids a hydration mismatch). */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function studentIdFromStoredToken(): string | null {
  const token = getAccessToken();
  if (!token) return null;
  return decodeJwtPayload<AccessTokenClaims>(token)?.sub ?? null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [studentId, setStudentId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // `token-store.ts` is backed by localStorage, which doesn't exist on
    // the server — the server-rendered HTML always shows "no session"
    // (isLoading=true, studentId=null), and this effect performs the one
    // client-only read that corrects it. `useSyncExternalStore` looks
    // like the "proper" tool here, but in practice its client resync
    // isn't guaranteed to land before a redirect effect elsewhere reads
    // the still-server-matched (unauthenticated) snapshot — verified by
    // hand: it fired a spurious redirect to /login on an authenticated
    // reload. This explicit load-then-setState avoids that: isLoading
    // only flips once studentId is already correct in the same update.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStudentId(studentIdFromStoredToken());
    setIsLoading(false);
    return subscribe(() => setStudentId(studentIdFromStoredToken()));
  }, []);

  const applyTokens = useCallback((tokens: TokenResponse) => {
    setTokens(tokens);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      applyTokens(await authApi.login(email, password));
    },
    [applyTokens],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      applyTokens(await authApi.register(email, password, fullName));
    },
    [applyTokens],
  );

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    clearTokens();
    if (refreshToken) {
      await authApi.logout(refreshToken).catch(() => {
        // Best-effort — the tokens are already cleared client-side either way.
      });
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{ studentId, isAuthenticated: studentId !== null, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
