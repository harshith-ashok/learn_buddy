"use client";

import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useUploadDocument } from "@/lib/hooks/use-documents";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".pptx"];

export function UploadDropzone() {
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [examDate, setExamDate] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadDocument();

  function uploadFile(file: File) {
    upload.mutate({ file, examDate: examDate || undefined });
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDraggingOver(false);
    const file = event.dataTransfer.files[0];
    if (file) uploadFile(file);
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) uploadFile(file);
    event.target.value = "";
  }

  return (
    <div className="flex flex-col gap-4">
      <label className="flex w-fit flex-col gap-1.5 text-[13px] text-ink-muted">
        Exam date (optional) — used to prioritize recommendations as it approaches
        <input
          type="date"
          value={examDate}
          onChange={(event) => setExamDate(event.target.value)}
          className="rounded-control border border-border bg-transparent px-3 py-2 text-ink outline-none focus:border-brand-500"
        />
      </label>

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDraggingOver(true);
        }}
        onDragLeave={() => setIsDraggingOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2.5 rounded-card border border-dashed px-6 py-14 text-center transition-colors ${
          isDraggingOver
            ? "border-brand-500 bg-surface-raised text-ink-muted"
            : "border-border text-ink-faint hover:border-brand-500 hover:bg-surface-raised hover:text-ink-muted"
        }`}
      >
        {upload.isPending ? (
          <Spinner label="Uploading…" />
        ) : (
          <>
            <svg width="26" height="26" viewBox="0 0 16 16" fill="none">
              <path
                d="M8 11V3M5 6l3-3 3 3"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2.5 11v2a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-2"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-[14.5px] font-semibold text-ink">
              Drop a file here, or click to browse
            </span>
            <span className="text-[12.5px] text-ink-faint">
              Accepted: {ACCEPTED_EXTENSIONS.join(", ")} — up to 25MB
            </span>
          </>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          onChange={handleFileInput}
          className="hidden"
        />
      </div>

      {upload.isError && <ErrorBanner error={upload.error} />}
    </div>
  );
}
