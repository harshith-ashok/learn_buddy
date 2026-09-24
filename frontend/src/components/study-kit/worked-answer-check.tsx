"use client";

import { useState } from "react";
import { useGradeWorkedAnswer } from "@/lib/hooks/use-worked-answer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { AgentActivity } from "@/components/topic/agent-activity";
import type { WorkedStepFeedback } from "@/lib/types";

const GRADE_STAGES = [
  { label: "READING YOUR WORK" },
  { label: "CHECKING AGAINST REFERENCE" },
  { label: "LOCATING FIRST ERROR" },
  { label: "UPDATING MASTERY" },
];

const VERDICT_COLOR: Record<WorkedStepFeedback["verdict"], string> = {
  correct: "text-moss",
  incorrect: "text-rust",
  unclear: "text-mustard",
};

export function WorkedAnswerCheck({ studyKitId, problemIndex }: { studyKitId: string; problemIndex: number }) {
  const [work, setWork] = useState("");
  const grade = useGradeWorkedAnswer(studyKitId, problemIndex);
  const result = grade.data;

  function handleSubmit() {
    if (!work.trim() || grade.isPending) return;
    grade.mutate(work);
  }

  return (
    <div className="mt-4 border-t border-border-soft pt-4">
      <div className="mb-2.5 text-[11px] tracking-[0.08em] text-ink-faint">CHECK MY WORK</div>
      <textarea
        value={work}
        onChange={(event) => setWork(event.target.value)}
        placeholder="Write out your steps here…"
        rows={4}
        disabled={grade.isPending}
        className="w-full resize-y rounded-control border border-border bg-transparent px-3.5 py-2.5 text-[13.5px] leading-relaxed text-ink outline-none focus:border-brand-500 disabled:opacity-60"
      />

      <div className="mt-3 flex flex-col gap-4">
        <AgentActivity stages={GRADE_STAGES} active={grade.isPending} />
        {grade.isError && <ErrorBanner error={grade.error} />}

        {result && !result.covered && (
          <p className="text-[13px] text-ink-muted">{result.overall_feedback}</p>
        )}

        {result && result.covered && (
          <div className={`border-l-2 py-0.5 pl-4 ${result.is_correct ? "border-moss" : "border-rust"}`}>
            <div className="mb-2 flex items-center gap-3">
              <Badge tone={result.is_correct ? "success" : "danger"}>
                {result.is_correct ? "Correct" : "Not quite"}
              </Badge>
              <span className="text-sm text-ink">{Math.round(result.accuracy_score * 100)}% of steps right</span>
            </div>
            <p className="mb-3 text-[13px] text-ink-muted">{result.overall_feedback}</p>

            {result.step_feedback.length > 0 && (
              <ol className="mb-3 flex flex-col gap-2">
                {result.step_feedback.map((step) => (
                  <li key={step.step_number} className="text-[13px] leading-relaxed">
                    <span
                      className={`mr-2 font-mono text-xs ${
                        step.step_number === result.first_error_step ? "text-rust" : "text-ink-faint"
                      }`}
                    >
                      {String(step.step_number).padStart(2, "0")}
                    </span>
                    <span className={`font-medium ${VERDICT_COLOR[step.verdict]}`}>{step.verdict}</span>
                    <span className="text-ink-muted"> — {step.feedback}</span>
                  </li>
                ))}
              </ol>
            )}

            {result.new_mastery_score !== null && result.previous_mastery_score !== null && (
              <p className="mb-3 text-[13px] text-ink-muted">
                Mastery: {Math.round(result.previous_mastery_score * 100)}% →{" "}
                {Math.round(result.new_mastery_score * 100)}%
              </p>
            )}

            {result.remediation && (
              <div className="mb-3 max-w-[56ch] rounded-control border border-mustard/30 bg-mustard-tint p-4 text-sm">
                <p className="mb-2 font-medium text-mustard">{result.remediation.message}</p>
                <ul className="list-inside list-disc text-ink-muted">
                  {result.remediation.suggested_actions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <Button
          variant="secondary"
          onClick={handleSubmit}
          disabled={grade.isPending || work.trim().length === 0}
          className="self-start"
        >
          {grade.isPending ? "Working…" : result ? "Check again" : "Check my work"}
        </Button>
      </div>
    </div>
  );
}
