export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-brand-500" />
      {label}
    </div>
  );
}
