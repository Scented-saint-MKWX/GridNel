"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { decodeJwt, isExpired, setToken as setStoredToken } from "@/lib/auth";
import type { JwtPayload } from "@/types/auth";

interface AuthContextValue {
  payload: JwtPayload | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// A single QueryClient per app instance. Cleared explicitly on logout so no
// privileged response (e.g. a trajectory) survives a role switch in cache.
function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: 1, staleTime: 5_000 } },
  });
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  const [payload, setPayload] = useState<JwtPayload | null>(null);

  const login = useCallback(
    (token: string) => {
      const decoded = decodeJwt(token);
      if (!decoded || isExpired(decoded)) {
        setStoredToken(null);
        setPayload(null);
        return;
      }
      setStoredToken(token);
      setPayload(decoded);
    },
    [],
  );

  const logout = useCallback(() => {
    setStoredToken(null);
    setPayload(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo(() => ({ payload, login, logout }), [payload, login, logout]);

  return (
    <AuthContext.Provider value={value}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
