"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <main className="flex flex-1 flex-col">{children}</main>;
  }

  return (
    <div className="flex min-h-full w-full flex-1">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}
