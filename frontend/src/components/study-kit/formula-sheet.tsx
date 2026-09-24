import type { Formula } from "@/lib/types";
import { Latex } from "@/components/ui/latex";

export function FormulaSheet({ formulas }: { formulas: Formula[] | undefined }) {
  // Defensive: the backend backfills `formulas: []` for study kits
  // generated before this field existed, but this guards against any
  // other stale/cached response shape reaching the client with the key
  // missing outright rather than crashing on `.length`.
  if (!formulas || formulas.length === 0) return null;

  return (
    <div className="mt-8 border-t border-border pt-6">
      <div className="mb-4 text-[11px] tracking-[0.08em] text-ink-faint">FORMULAS</div>
      <div className="flex flex-col gap-4">
        {formulas.map((formula, index) => (
          <div key={index} className="rounded-card border border-border bg-surface-raised px-5 py-4">
            <div className="mb-2 text-[13px] font-medium text-ink">{formula.label}</div>
            <Latex expr={formula.latex} display className="block overflow-x-auto text-ink" />
            {formula.description && (
              <p className="mt-2 text-[12.5px] leading-relaxed text-ink-muted">{formula.description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
