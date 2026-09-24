"use client";

import { useEffect, useRef, useState } from "react";
import { useFeynmanHistory, useGradeFeynman } from "@/lib/hooks/use-feynman";
import type { FeynmanAttemptOut, FeynmanBreakdownPoint } from "@/lib/types";
import { AgentActivity } from "@/components/topic/agent-activity";
import { Badge } from "@/components/ui/badge";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";

const GRADE_STAGES = [
  { label: "RETRIEVING TOPIC CONTEXT" },
  { label: "CHECKING COVERAGE" },
  { label: "GRADING EXPLANATION" },
  { label: "UPDATING MASTERY" },
];

const VERDICT_TONE: Record<FeynmanBreakdownPoint["verdict"], "success" | "warning" | "danger"> = {
  correct: "success",
  incomplete: "warning",
  incorrect: "danger",
};

function AttemptCard({ attempt }: { attempt: FeynmanAttemptOut }) {
  return (
    <div className="border-b border-border-soft py-4 last:border-b-0">
      <div className="mb-1.5 flex items-center gap-2">
        <span className="h-[6px] w-[6px] rounded-full bg-ink-faint" />
        <span className="font-mono text-[11px] tracking-wide text-ink-faint">YOUR EXPLANATION</span>
      </div>
      <p className="mb-3 text-[14px] leading-relaxed text-ink">{attempt.explanation}</p>

      <div className="mb-2 flex items-center gap-3">
        <span className="font-mono text-lg text-brand-500">{Math.round(attempt.accuracy_score * 100)}%</span>
        <span className="text-[13px] text-ink-muted">{attempt.overall_feedback}</span>
      </div>

      {attempt.breakdown.length > 0 && (
        <ul className="mt-2 flex flex-col gap-2">
          {attempt.breakdown.map((point, index) => (
            <li key={index} className="flex flex-wrap items-start gap-2 text-[13px]">
              <Badge tone={VERDICT_TONE[point.verdict]}>{point.verdict}</Badge>
              <span className="text-ink-muted">
                <span className="text-ink">{point.claim}</span> — {point.feedback}
              </span>
            </li>
          ))}
        </ul>
      )}

      {attempt.missing_concepts.length > 0 && (
        <p className="mt-3 text-[12.5px] text-ink-faint">
          Didn&apos;t mention: {attempt.missing_concepts.join(", ")}
        </p>
      )}
    </div>
  );
}

export function FeynmanMode({ topicId, topicName }: { topicId: string; topicName: string }) {
  const history = useFeynmanHistory(topicId);
  const grade = useGradeFeynman(topicId);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const attempts = history.data ?? [];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [attempts.length, grade.isPending]);

  function handleSubmit() {
    const explanation = draft.trim();
    if (!explanation || grade.isPending) return;
    setDraft("");
    grade.mutate(explanation);
  }

  return (
    <div className="mt-3">
      <div className="mb-4.5 text-[11px] tracking-[0.08em] text-ink-faint">
        FEYNMAN MODE — EXPLAIN IT BACK
      </div>
      <p className="mb-4 max-w-[62ch] text-[13px] leading-relaxed text-ink-muted">
        Explain <span className="text-ink-muted">{topicName}</span> in your own words. Grading checks your
        explanation against this topic&apos;s own material and shows exactly where it breaks down —
        recall isn&apos;t enough here.
      </p>

      <div
        ref={scrollRef}
        className="max-h-[420px] overflow-y-auto rounded-card border border-border bg-surface-raised px-5"
      >
        {history.isPending && (
          <div className="py-6">
            <Spinner label="Loading past attempts…" />
          </div>
        )}
        {history.isError && (
          <div className="py-4">
            <ErrorBanner error={history.error} />
          </div>
        )}
        {history.data && attempts.length === 0 && !grade.isPending && !grade.data && (
          <p className="py-6 text-[13px] text-ink-faint">No attempts yet — try explaining it below.</p>
        )}
        {attempts.map((attempt) => (
          <AttemptCard key={attempt.id} attempt={attempt} />
        ))}
        {grade.isPending && (
          <div className="py-4">
            <AgentActivity stages={GRADE_STAGES} active />
          </div>
        )}
        {grade.isError && (
          <div className="py-4">
            <ErrorBanner error={grade.error} />
          </div>
        )}
        {grade.data && !grade.data.covered && (
          <p className="py-4 text-[13px] text-ink-muted">{grade.data.overall_feedback}</p>
        )}
        {grade.data?.remediation && (
          <div className="my-4 max-w-[56ch] rounded-control border border-mustard/30 bg-mustard-tint p-4 text-sm">
            <p className="mb-2 font-medium text-mustard">{grade.data.remediation.message}</p>
            <ul className="list-inside list-disc text-ink-muted">
              {grade.data.remediation.suggested_actions.map((action, index) => (
                <li key={index}>{action}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-col gap-2.5">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={`Explain ${topicName} as if teaching someone new to it…`}
          rows={4}
          disabled={grade.isPending}
          className="w-full resize-y rounded-control border border-border bg-transparent px-3.5 py-2.5 text-[13.5px] leading-relaxed text-ink outline-none focus:border-brand-500 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={grade.isPending || draft.trim().length === 0}
          className="self-start rounded-control bg-brand-500 px-5 py-2.5 text-[13.5px] font-semibold text-surface transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-200 disabled:text-ink-faint"
        >
          {grade.isPending ? "Working…" : "Grade my explanation"}
        </button>
      </div>
    </div>
  );
}
