interface ChainNode {
  id: string;
  name: string;
}

interface PrerequisiteChainProps {
  label: string;
  nodes: ChainNode[];
  current: ChainNode;
  /** "before" places `current` last (a prerequisite chain); "after" places it first (what it unlocks). */
  position: "before" | "after";
}

export function PrerequisiteChain({ label, nodes, current, position }: PrerequisiteChainProps) {
  const ordered = position === "before" ? [...nodes, current] : [current, ...nodes];

  return (
    <div className="mt-7">
      <div className="mb-4.5 text-[11px] tracking-[0.08em] text-ink-faint">{label}</div>
      {ordered.length === 1 ? (
        <p className="text-[13px] text-ink-faint">None yet.</p>
      ) : (
        <div className="flex flex-wrap items-start">
          {ordered.map((node, index) => (
            <div className="contents" key={node.id}>
              <div className="flex w-24 flex-col items-center gap-2 text-center">
                <span
                  className={`h-[9px] w-[9px] rounded-full border-2 border-surface-raised ${
                    node.id === current.id ? "bg-brand-500" : "bg-border"
                  }`}
                />
                <span
                  className={`text-[11.5px] leading-tight ${
                    node.id === current.id ? "font-semibold text-ink" : "text-ink-muted"
                  }`}
                >
                  {node.name}
                </span>
              </div>
              {index < ordered.length - 1 && (
                <div className="mt-1 h-px min-w-4 flex-1 bg-border" />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
