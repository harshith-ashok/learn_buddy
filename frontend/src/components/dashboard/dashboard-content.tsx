"use client";

import { useMemo, useState } from "react";
import { useDocuments } from "@/lib/hooks/use-documents";
import { useProgress } from "@/lib/hooks/use-progress";
import { RecommendedNext } from "@/components/dashboard/recommended-next";
import { RemediationAlert } from "@/components/dashboard/remediation-alert";
import { UnitFilters } from "@/components/dashboard/unit-filters";
import { TopicLedger } from "@/components/dashboard/topic-ledger";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";

const ALL_DOCUMENTS = "ALL";

export function DashboardContent() {
  const progress = useProgress();
  const { data: documents } = useDocuments();
  const [activeDocument, setActiveDocument] = useState(ALL_DOCUMENTS);

  const documentNames = useMemo(() => {
    const names = new Map<string, string>();
    for (const document of documents ?? []) names.set(document.id, document.filename);
    return names;
  }, [documents]);

  const visibleTopics = useMemo(() => {
    const topics = progress.data?.topics ?? [];
    if (activeDocument === ALL_DOCUMENTS) return topics;
    return topics.filter((topic) => topic.document_id === activeDocument);
  }, [progress.data, activeDocument]);

  return (
    <div className="mx-auto grid w-full max-w-295 gap-14 px-8 pb-32 pt-10 md:grid-cols-[300px_1fr]">
      <aside className="flex flex-col gap-8 md:sticky md:top-22 md:self-start">
        <div className="animate-rise" style={{ animationDelay: "160ms" }}>
          <span className="mb-3.5 block text-[11px] tracking-[0.08em] text-ink-faint">
            RECOMMENDED NEXT
          </span>
          <RecommendedNext />
        </div>

        <RemediationAlert topics={progress.data?.topics} documentNames={documentNames} />

        {documents && documents.length > 0 && (
          <div>
            <span className="mb-3.5 block text-[11px] tracking-[0.08em] text-ink-faint">
              FILTER BY DOCUMENT
            </span>
            <UnitFilters
              documents={documents}
              active={activeDocument}
              onChange={setActiveDocument}
              allValue={ALL_DOCUMENTS}
            />
          </div>
        )}
      </aside>

      <section>
        <div className="mb-1 flex items-baseline justify-between gap-4 border-b border-border pb-3.5">
          <h2 className="text-[22px] font-normal text-ink">All topics</h2>
          <span className="font-mono text-xs text-ink-faint">
            {visibleTopics.length} · updates after every quiz
          </span>
        </div>

        {progress.isPending && (
          <div className="py-10">
            <Spinner label="Loading your ledger…" />
          </div>
        )}
        {progress.isError && (
          <div className="py-6">
            <ErrorBanner error={progress.error} />
          </div>
        )}
        {progress.data && (
          <TopicLedger topics={visibleTopics} documentNames={documentNames} />
        )}
      </section>
    </div>
  );
}
