"use client";

import { useState } from "react";
import { useSubmitQuiz } from "@/lib/hooks/use-quiz";
import type { QuizContent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { AgentActivity } from "@/components/topic/agent-activity";

// Mirrors `score_and_update_mastery` -> `trigger_remediation` (wiki/agent-design.md).
const GRADING_STAGES = [
  { label: "SCORING ANSWERS" },
  { label: "UPDATING MASTERY" },
  { label: "CHECKING FOR REMEDIATION" },
];

interface QuizViewProps {
  content: QuizContent;
  topicId: string;
  studyKitId: string;
}

export function QuizView({ content, topicId, studyKitId }: QuizViewProps) {
  const [selected, setSelected] = useState<Record<number, number>>({});
  const submitQuiz = useSubmitQuiz(topicId, studyKitId);

  const allAnswered = content.questions.every((_, index) => selected[index] !== undefined);
  const result = submitQuiz.data;

  function handleSubmit() {
    submitQuiz.mutate(
      content.questions.map((_, index) => ({
        question_index: index,
        selected_index: selected[index],
      })),
    );
  }

  function handleRetake() {
    setSelected({});
    submitQuiz.reset();
  }

  return (
    <div className="flex flex-col gap-9">
      {content.questions.map((question, questionIndex) => (
        <div key={questionIndex} className="max-w-[56ch]">
          <p className="mb-4.5 text-base font-medium text-ink">{question.question}</p>
          <div className="flex flex-col gap-2.5">
            {question.options.map((option, optionIndex) => {
              const isSelected = selected[questionIndex] === optionIndex;
              return (
                <label
                  key={optionIndex}
                  className={`block max-w-120 cursor-pointer rounded-control border px-4 py-3.5 text-[13.5px] transition-colors ${
                    isSelected ? "border-brand-500 text-ink" : "border-border text-ink-muted hover:border-ink-muted"
                  } ${result !== undefined ? "cursor-default" : ""}`}
                >
                  <input
                    type="radio"
                    name={`question-${questionIndex}`}
                    disabled={result !== undefined}
                    checked={isSelected}
                    onChange={() =>
                      setSelected((current) => ({ ...current, [questionIndex]: optionIndex }))
                    }
                    className="sr-only"
                  />
                  {option}
                </label>
              );
            })}
          </div>
        </div>
      ))}

      {submitQuiz.isError && <ErrorBanner error={submitQuiz.error} />}

      {result === undefined ? (
        <div className="flex flex-col gap-4">
          <AgentActivity stages={GRADING_STAGES} active={submitQuiz.isPending} />
          <Button onClick={handleSubmit} disabled={!allAnswered || submitQuiz.isPending} className="self-start">
            {submitQuiz.isPending ? "Working…" : "Submit quiz"}
          </Button>
        </div>
      ) : (
        <div className="border-l-2 border-moss py-0.5 pl-4">
          <div className="mb-2 flex items-center gap-3">
            <Badge tone={result.is_pass ? "success" : "danger"}>
              {result.is_pass ? "Passed" : "Not quite"}
            </Badge>
            <span className="text-sm text-ink">{Math.round(result.score * 100)}% correct</span>
          </div>
          <p className="mb-4 text-[13px] text-ink-muted">
            Mastery: {Math.round(result.previous_mastery_score * 100)}% →{" "}
            {Math.round(result.new_mastery_score * 100)}%
          </p>
          {result.remediation && (
            <div className="mb-4 max-w-[56ch] rounded-control border border-mustard/30 bg-mustard-tint p-4 text-sm">
              <p className="mb-2 font-medium text-mustard">{result.remediation.message}</p>
              <ul className="list-inside list-disc text-ink-muted">
                {result.remediation.suggested_actions.map((action, index) => (
                  <li key={index}>{action}</li>
                ))}
              </ul>
            </div>
          )}
          <Button variant="secondary" onClick={handleRetake}>
            Retake
          </Button>
        </div>
      )}
    </div>
  );
}
