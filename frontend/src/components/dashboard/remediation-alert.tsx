"use client";

import Link from "next/link";
import type { TopicProgressOut } from "@/lib/types";

interface RemediationAlertProps {
  topics: TopicProgressOut[] | undefined;
  documentNames: Map<string, string>;
}

/** Surfaces the single topic most in need of review — the one with the most consecutive quiz misses. */
export function RemediationAlert({ topics, documentNames }: RemediationAlertProps) {
  const struggling = (topics ?? [])
    .filter((topic) => topic.consecutive_failures >= 2)
    .sort((a, b) => b.consecutive_failures - a.consecutive_failures)[0];

  if (!struggling) return null;

  const unit = documentNames.get(struggling.document_id);

  return (
    <Link
      href={`/study-kit/${struggling.topic_id}`}
      className="group flex items-start gap-3 border-l-2 border-rust py-1 pl-4 text-left"
    >
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" className="mt-0.5 flex-none text-rust">
        <path
          d="M8 5.5v3.5M8 11.2h.01M1.5 13.5h13L8 2 1.5 13.5Z"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
      </svg>
      <div>
        <div className="mb-1 text-[13px] font-semibold text-ink transition-colors group-hover:text-rust">
          {struggling.topic_name} needs review
        </div>
        <p className="text-[12.5px] leading-relaxed text-ink-muted">
          {struggling.consecutive_failures} quiz attempts missed in a row
          {unit ? ` · ${unit}` : ""}. Generate a fresh study kit to shore it up.
        </p>
      </div>
    </Link>
  );
}
