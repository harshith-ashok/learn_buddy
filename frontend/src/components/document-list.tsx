"use client";

import Link from "next/link";
import { useDocuments } from "@/lib/hooks/use-documents";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import type { DocumentStatus } from "@/lib/types";

const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "Queued",
  processing: "Ingesting…",
  done: "Parsed",
  failed: "Failed",
};

const STATUS_PROGRESS: Record<DocumentStatus, number> = {
  pending: 12,
  processing: 60,
  done: 100,
  failed: 100,
};

export function DocumentList() {
  const { data: documents, isPending, isError, error } = useDocuments();

  if (isPending) return <Spinner label="Loading your documents…" />;
  if (isError) return <ErrorBanner error={error} />;
  if (documents.length === 0) {
    return <p className="text-sm text-ink-muted">No documents uploaded yet.</p>;
  }

  return (
    <div className="flex flex-col gap-2.5">
      {documents.map((document) => {
        const isDone = document.status === "done";
        const isFailed = document.status === "failed";
        return (
          <div
            key={document.id}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-3.5 rounded-card border border-border p-4"
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" className="text-ink-faint">
              <path d="M4 1.5h6l3 3v10H4z" stroke="currentColor" strokeWidth="1.2" />
              <path d="M9.5 1.5V5h3.5" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            <div className="flex min-w-0 flex-col gap-1">
              <span className="truncate text-[13.5px] font-medium text-ink">{document.filename}</span>
              {document.exam_date && (
                <span className="text-[11.5px] text-ink-faint">
                  Exam: {new Date(document.exam_date).toLocaleDateString()}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3.5">
              <span
                className={`whitespace-nowrap text-[11.5px] ${
                  isDone ? "text-moss" : isFailed ? "text-rust" : "text-ink-faint"
                }`}
              >
                {STATUS_LABEL[document.status]}
              </span>
              {isDone && (
                <Link
                  href="/dashboard"
                  className="whitespace-nowrap text-[12.5px] font-medium text-brand-500 hover:underline"
                >
                  View topics
                </Link>
              )}
            </div>
            <div className="col-span-3 mt-0.5 h-0.75 overflow-hidden rounded-full bg-surface-sunken">
              <div
                className={`h-full transition-[width] duration-400 ${
                  isDone ? "bg-moss" : isFailed ? "bg-rust" : "bg-brand-500"
                }`}
                style={{ width: `${STATUS_PROGRESS[document.status]}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
