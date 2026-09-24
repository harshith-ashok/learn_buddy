"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

let browserQueryClient: QueryClient | undefined;

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          // A 401/403/404 won't succeed on retry — only retry transient failures.
          if (error instanceof ApiError && error.status < 500) return false;
          return failureCount < 2;
        },
        staleTime: 30_000,
      },
    },
  });
}

function getQueryClient(): QueryClient {
  // Keep server-render requests isolated; reuse one client in the browser.
  if (typeof window === "undefined") return createQueryClient();
  browserQueryClient ??= createQueryClient();
  return browserQueryClient;
}

export function Providers({ children }: { children: ReactNode }) {
  const queryClient = getQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
