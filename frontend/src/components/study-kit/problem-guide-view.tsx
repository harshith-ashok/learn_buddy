import type { ProblemGuideContent } from "@/lib/types";
import { FormulaSheet } from "@/components/study-kit/formula-sheet";
import { WorkedAnswerCheck } from "@/components/study-kit/worked-answer-check";

export function ProblemGuideView({
  content,
  studyKitId,
}: {
  content: ProblemGuideContent;
  studyKitId: string;
}) {
  return (
    <div>
      <div className="flex flex-col gap-9">
        {content.problems.map((problem, problemIndex) => (
          <div key={problemIndex} className="max-w-[62ch]">
            <p className="mb-4 text-base font-medium text-ink">{problem.prompt}</p>
            <ol className="flex flex-col gap-4">
              {problem.steps.map((step, stepIndex) => (
                <li key={stepIndex} className="flex gap-4 text-[13.5px] leading-relaxed text-ink-muted">
                  <span className="flex-none pt-px font-mono text-xs text-brand-500">
                    {String(stepIndex + 1).padStart(2, "0")}
                  </span>
                  {step.text}
                </li>
              ))}
            </ol>
            <WorkedAnswerCheck studyKitId={studyKitId} problemIndex={problemIndex} />
          </div>
        ))}
      </div>
      <FormulaSheet formulas={content.formulas} />
    </div>
  );
}
