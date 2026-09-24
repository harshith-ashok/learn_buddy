"use client";

import Link from "next/link";
import type { TopicProgressOut } from "@/lib/types";
import { MasteryTicks } from "@/components/ui/mastery-ticks";

interface TopicLedgerProps {
  topics: TopicProgressOut[];
  documentNames: Map<string, string>;
}

export function TopicLedger({ topics, documentNames }: TopicLedgerProps) {
  if (topics.length === 0) {
    return (
      <p className="py-10 text-sm text-ink-muted">
        No topics yet — upload a document to get started.
      </p>
    );
  }

  return (
    <div>
      {topics.map((topic, index) => (
        <Link
          key={topic.topic_id}
          href={`/study-kit/${topic.topic_id}`}
          className="animate-rise group grid grid-cols-[30px_1fr_150px_74px_16px] items-center gap-5 border-b border-border-soft py-[18px] text-left transition-[background,margin,padding] duration-150 hover:mx-[-14px] hover:bg-surface-raised hover:px-3.5 max-[560px]:grid-cols-[26px_1fr_60px_14px]"
          style={{ animationDelay: `${index * 45}ms` }}
        >
          <span className="font-mono text-xs text-ink-faint">
            {String(index + 1).padStart(2, "0")}
          </span>
          <span className="min-w-0">
            <span className="block text-base font-medium text-ink">{topic.topic_name}</span>
            <span className="mt-0.5 flex items-center gap-1.5 text-[11.5px] text-ink-faint">
              {documentNames.get(topic.document_id) ?? "Untitled document"}
              {topic.consecutive_failures >= 2 && (
                <span className="font-semibold text-rust before:mr-1 before:content-['•']">
                  needs remediation
                </span>
              )}
            </span>
          </span>
          <span className="max-[560px]:hidden">
            <MasteryTicks score={topic.mastery_score} />
          </span>
          <span className="text-right font-mono text-xl text-ink">
            {Math.round(topic.mastery_score * 100)}
            <small className="text-xs text-ink-faint">%</small>
          </span>
          <span className="text-ink-faint transition-[transform,color] duration-150 group-hover:translate-x-[3px] group-hover:text-ink">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path
                d="M6 3l5 5-5 5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </Link>
      ))}
    </div>
  );
}
