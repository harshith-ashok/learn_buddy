import type { SummaryContent } from "@/lib/types";
import { FormulaSheet } from "@/components/study-kit/formula-sheet";

export function SummaryView({ content }: { content: SummaryContent }) {
  return (
    <div className="max-w-[68ch]">
      <div className="text-[15px] leading-[1.75] text-ink">
        {content.points.map((point, index) => (
          <p
            key={index}
            className={index === 0 ? "mb-4 first-letter:float-left first-letter:pr-2 first-letter:pt-1 first-letter:font-serif first-letter:text-[44px] first-letter:font-bold first-letter:leading-[0.85] first-letter:text-brand-500" : "mb-4"}
          >
            {point.text}
          </p>
        ))}
      </div>
      <FormulaSheet formulas={content.formulas} />
    </div>
  );
}
