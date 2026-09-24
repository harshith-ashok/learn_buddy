"use client";

import type { DocumentOut } from "@/lib/types";

interface UnitFiltersProps {
  documents: DocumentOut[];
  active: string;
  allValue: string;
  onChange: (value: string) => void;
}

export function UnitFilters({ documents, active, allValue, onChange }: UnitFiltersProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        aria-pressed={active === allValue}
        onClick={() => onChange(allValue)}
        className={`rounded-full border px-[13px] py-[7px] text-[12.5px] transition-colors ${
          active === allValue
            ? "border-ink bg-ink text-surface"
            : "border-border text-ink-muted hover:border-ink-muted hover:text-ink"
        }`}
      >
        All
      </button>
      {documents.map((document) => (
        <button
          key={document.id}
          type="button"
          aria-pressed={active === document.id}
          onClick={() => onChange(document.id)}
          className={`max-w-[220px] truncate rounded-full border px-[13px] py-[7px] text-[12.5px] transition-colors ${
            active === document.id
              ? "border-ink bg-ink text-surface"
              : "border-border text-ink-muted hover:border-ink-muted hover:text-ink"
          }`}
        >
          {document.filename}
        </button>
      ))}
    </div>
  );
}
