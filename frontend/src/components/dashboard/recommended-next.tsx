"use client";

import Link from "next/link";
import { useRecommendation } from "@/lib/hooks/use-recommendation";
import { isRecommendation } from "@/lib/types";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";

export function RecommendedNext() {
  const { data, isPending, isError, error } = useRecommendation();

  if (isPending) return <Spinner label="Finding your next topic…" />;
  if (isError) return <ErrorBanner error={error} />;
  if (!isRecommendation(data)) {
    return <p className="max-w-[40ch] text-[13.5px] leading-relaxed text-ink-muted">{data.reason}</p>;
  }

  const percent = Math.round(data.mastery_score * 100);

  return (
    <div>
      <div className="font-mono text-[64px] leading-[0.9] text-brand-500 sm:text-[84px]">
        {percent}
        <sup className="top-[-0.5em] text-3xl sm:text-4xl">%</sup>
      </div>
      <h3 className="mt-1.5 mb-2.5 text-2xl font-semibold text-ink sm:text-[28px]">
        {data.topic_name}
      </h3>
      <p className="mb-4.5 max-w-[40ch] text-[13.5px] leading-relaxed text-ink-muted">
        {data.justification}
      </p>
      <Link
        href={`/study-kit/${data.topic_id}`}
        className="group inline-flex items-center gap-2 rounded-control bg-brand-500 px-[18px] py-3 text-[13.5px] font-semibold text-surface transition-all duration-150 ease-out hover:translate-x-0.5 hover:bg-brand-700"
      >
        Open topic
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="transition-transform duration-150 group-hover:translate-x-[3px]">
          <path
            d="M3 8h10M9 4l4 4-4 4"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </Link>
    </div>
  );
}
