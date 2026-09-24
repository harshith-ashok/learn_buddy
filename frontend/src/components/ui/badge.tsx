import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "brand";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "border-border text-ink-muted",
  success: "border-moss/40 text-moss",
  warning: "border-mustard/40 text-mustard",
  danger: "border-rust/40 text-rust",
  brand: "border-brand-500/40 text-brand-500",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 font-mono text-[11px] tracking-wide ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}
