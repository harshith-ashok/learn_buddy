"use client";

import { useEffect, useRef, useState } from "react";
import { masteryColor } from "@/components/ui/mastery-ticks";

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** A circular mastery-percent ring that animates in when `score` changes. */
export function MasteryDial({ score }: { score: number }) {
  const percent = Math.round(Math.min(1, Math.max(0, score)) * 100);
  const [offset, setOffset] = useState(CIRCUMFERENCE);
  const frame = useRef<number | undefined>(undefined);

  useEffect(() => {
    frame.current = requestAnimationFrame(() => {
      setOffset(CIRCUMFERENCE - (CIRCUMFERENCE * percent) / 100);
    });
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [percent]);

  const color = masteryColor(score);

  return (
    <div className="flex-none text-center">
      <svg width="104" height="104" viewBox="0 0 104 104">
        <circle
          cx="52"
          cy="52"
          r="47"
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="1"
          strokeDasharray="1 6.2"
        />
        <circle
          cx="52"
          cy="52"
          r={RADIUS}
          fill="none"
          stroke="var(--color-border-soft)"
          strokeWidth="8"
        />
        <circle
          cx="52"
          cy="52"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 52 52)"
          style={{ transition: "stroke-dashoffset 700ms cubic-bezier(.2,.8,.2,1)" }}
        />
        <text
          x="52"
          y="58"
          textAnchor="middle"
          className="font-mono"
          fontSize="20"
          fill="var(--color-ink)"
        >
          {percent}%
        </text>
      </svg>
      <span className="mt-2 block text-[11px] tracking-[0.06em] text-ink-faint">MASTERY</span>
    </div>
  );
}
