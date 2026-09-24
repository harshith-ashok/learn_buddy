const TICK_COUNT = 20;

export function masteryColor(score: number): string {
  const percent = score * 100;
  if (percent < 45) return "var(--color-rust)";
  if (percent < 70) return "var(--color-mustard)";
  return "var(--color-moss)";
}

/** A row of filled/unfilled ticks representing mastery, like a levels meter. */
export function MasteryTicks({ score }: { score: number }) {
  const percent = Math.round(Math.min(1, Math.max(0, score)) * 100);
  const filled = Math.round((percent / 100) * TICK_COUNT);
  const color = masteryColor(score);

  return (
    <span
      className="flex items-end gap-[3px]"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      {Array.from({ length: TICK_COUNT }, (_, index) => (
        <i
          key={index}
          className="block h-[11px] w-[3px] rounded-[1px]"
          style={{ background: index < filled ? color : "var(--color-border)" }}
        />
      ))}
    </span>
  );
}
