"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useExamCountdown } from "@/lib/hooks/use-exam-countdown";

const MOBILE_LINKS = [
  { href: "/dashboard", label: "Ledger" },
  { href: "/upload", label: "Upload" },
];

function pageLabel(pathname: string | null): string {
  if (!pathname) return "";
  if (pathname.startsWith("/dashboard")) return "Ledger";
  if (pathname.startsWith("/upload")) return "Upload materials";
  if (pathname.startsWith("/study-kit")) return "Topic";
  return "";
}

export function Topbar() {
  const { logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const examDays = useExamCountdown();

  async function handleSignOut() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-10 flex h-16 flex-none items-center justify-between border-b border-border bg-surface px-6 md:px-8">
      <div className="flex items-center gap-5 md:hidden">
        <span className="text-[15px] font-bold text-ink">
          Study <em className="font-semibold text-brand-500 italic">Ledger</em>
        </span>
        <nav className="flex items-center gap-4">
          {MOBILE_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname?.startsWith(link.href) ? "page" : undefined}
              className={`text-[12.5px] ${
                pathname?.startsWith(link.href) ? "text-ink" : "text-ink-faint"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>

      <span className="hidden text-[13.5px] font-medium text-ink md:block">
        {pageLabel(pathname)}
      </span>

      <div className="flex items-center gap-5">
        {examDays !== null && (
          <span className="flex items-baseline gap-1.5 font-mono text-[12.5px] text-ink-muted">
            <span className="text-brand-500">{String(examDays).padStart(2, "0")}</span>
            days to exam
          </span>
        )}
        <button
          type="button"
          onClick={handleSignOut}
          className="text-[12.5px] text-ink-faint transition-colors hover:text-ink"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
