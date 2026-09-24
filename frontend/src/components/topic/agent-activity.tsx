"use client";

import { useEffect, useRef, useState } from "react";

export interface AgentStage {
  label: string;
}

interface AgentActivityProps {
  stages: AgentStage[];
  /** True while the request this activity represents is in flight. */
  active: boolean;
}

/**
 * A simulated node-by-node view of the LangGraph agent pipeline (see
 * `wiki/agent-design.md`) for a single request. The API is one
 * request/response call with no intermediate progress, so stage timing
 * here is a heuristic sequence, not a live trace — it disappears the
 * moment `active` goes false, handing off to the real result or an
 * `ErrorBanner` rendered by the caller.
 */
export function AgentActivity({ stages, active }: AgentActivityProps) {
  const [stageIndex, setStageIndex] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  // Reset to the first stage the moment `active` flips on — done during
  // render (React's documented pattern for resetting state when a prop
  // changes: https://react.dev/reference/react/useState#storing-information-from-previous-renders),
  // not as a side effect.
  const [wasActive, setWasActive] = useState(active);
  if (active !== wasActive) {
    setWasActive(active);
    if (active && stageIndex !== 0) setStageIndex(0);
  }

  useEffect(() => {
    if (!active) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    let index = 0;
    timer.current = setInterval(() => {
      index = Math.min(index + 1, stages.length - 1);
      setStageIndex(index);
    }, 900);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [active, stages.length]);

  if (!active) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col gap-2.5 rounded-card border border-border bg-surface-raised px-5 py-4"
    >
      {stages.map((stage, index) => {
        const isDone = index < stageIndex;
        const isCurrent = index === stageIndex;

        return (
          <div key={stage.label} className="flex items-center gap-3">
            <span className="relative flex h-2 w-2 flex-none items-center justify-center">
              {isCurrent && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-500 opacity-60" />
              )}
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  isDone ? "bg-moss" : isCurrent ? "bg-brand-500" : "bg-border"
                }`}
              />
            </span>
            <span
              className={`font-mono text-[12px] tracking-wide ${
                isDone ? "text-moss" : isCurrent ? "text-ink" : "text-ink-faint"
              }`}
            >
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
