"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  {
    href: "/dashboard",
    label: "Ledger",
    icon: (
      <path
        d="M3 4h10M3 8h10M3 12h6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    ),
  },
  {
    href: "/upload",
    label: "Upload materials",
    icon: (
      <>
        <path
          d="M8 11V3M5 6l3-3 3 3"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M2.5 11v2a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-2"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-screen w-64 flex-none flex-col border-r border-border bg-surface-raised md:flex">
      <div className="px-6 pb-6 pt-7">
        <span className="mb-1.5 block font-mono text-[11px] tracking-[0.06em] text-ink-faint">
          LEARN BUDDY
        </span>
        <span className="text-xl font-bold leading-none tracking-tight text-ink">
          Study <em className="font-semibold text-brand-500 italic">Ledger</em>
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3">
        {LINKS.map((link) => {
          const isActive = pathname?.startsWith(link.href) ?? false;
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex items-center gap-3 rounded-control border-l-2 px-3 py-2.5 text-[13.5px] transition-colors ${
                isActive
                  ? "border-brand-500 bg-surface-sunken text-ink"
                  : "border-transparent text-ink-muted hover:bg-surface-sunken/60 hover:text-ink"
              }`}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-none">
                {link.icon}
              </svg>
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
