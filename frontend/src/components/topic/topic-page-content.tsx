"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useProgress } from "@/lib/hooks/use-progress";
import { useCourseGraph } from "@/lib/hooks/use-course-graph";
import { MasteryDial } from "@/components/ui/mastery-dial";
import { PrerequisiteChain } from "@/components/topic/prerequisite-chain";
import { KitSection } from "@/components/topic/kit-section";
import { FeynmanMode } from "@/components/topic/feynman-mode";
import { TopicChat } from "@/components/topic/topic-chat";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";

export function TopicPageContent({ topicId }: { topicId: string }) {
  const progress = useProgress();
  const topicProgress = progress.data?.topics.find((topic) => topic.topic_id === topicId);
  const graph = useCourseGraph(topicProgress?.document_id);
  const node = graph.data?.topics.find((t) => t.id === topicId);

  const prerequisites = useMemo(
    () =>
      (node?.prerequisite_ids ?? [])
        .map((id) => graph.data?.topics.find((t) => t.id === id))
        .filter((t) => t !== undefined),
    [node, graph.data],
  );
  const unlocks = useMemo(
    () => (graph.data?.topics ?? []).filter((t) => t.prerequisite_ids.includes(topicId)),
    [graph.data, topicId],
  );

  return (
    <div className="mx-auto w-full max-w-295 px-8 pb-32 pt-10">
      <Link
        href="/dashboard"
        className="mb-7 inline-flex items-center gap-1.5 text-[13px] text-ink-muted transition-colors hover:text-ink"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <path
            d="M13 8H3M7 4 3 8l4 4"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Back to ledger
      </Link>

      {progress.isPending && <Spinner label="Loading topic…" />}
      {progress.isError && <ErrorBanner error={progress.error} />}

      {progress.data && !topicProgress && (
        <p className="text-sm text-ink-muted">Topic not found.</p>
      )}

      {topicProgress && (
        <>
          <div className="mb-10 flex flex-wrap justify-between gap-10">
            <div>
              <div className="mb-3 font-mono text-xs tracking-[0.08em] text-brand-500">
                {node?.position !== undefined ? `TOPIC ${node.position + 1}` : "TOPIC"}
              </div>
              <h2 className="max-w-[14ch] text-[34px] font-normal leading-[1.05] text-ink sm:text-[52px]">
                {topicProgress.topic_name}
              </h2>
              {node?.description && (
                <p className="mt-3.5 max-w-[46ch] text-[14.5px] leading-relaxed text-ink-muted">
                  {node.description}
                </p>
              )}
            </div>
            <MasteryDial score={topicProgress.mastery_score} />
          </div>

          <div className="mb-11 grid gap-6 lg:grid-cols-[1.3fr_1fr]">
            <div>
              <div className="mb-4.5 text-[11px] tracking-[0.08em] text-ink-faint">SUBTOPICS</div>
              {graph.isPending && <Spinner label="Loading subtopics…" />}
              {node && node.subtopics.length === 0 && (
                <p className="text-[13px] text-ink-faint">No subtopics recorded.</p>
              )}
              {node?.subtopics.map((subtopic) => (
                <div
                  key={subtopic.id}
                  className="border-b border-border-soft py-2.5 text-[13.5px] text-ink last:border-b-0"
                >
                  {subtopic.name}
                </div>
              ))}
            </div>
            <div>
              {node && (
                <>
                  <PrerequisiteChain
                    label="PREREQUISITE CHAIN"
                    nodes={prerequisites}
                    current={{ id: node.id, name: topicProgress.topic_name }}
                    position="before"
                  />
                  <PrerequisiteChain
                    label="UNLOCKS NEXT"
                    nodes={unlocks}
                    current={{ id: node.id, name: topicProgress.topic_name }}
                    position="after"
                  />
                </>
              )}
            </div>
          </div>

          <KitSection topicId={topicId} />

          <div className="mt-14 border-t border-border pt-11">
            <FeynmanMode topicId={topicId} topicName={topicProgress.topic_name} />
          </div>

          <div className="mt-14 border-t border-border pt-11">
            <TopicChat topicId={topicId} topicName={topicProgress.topic_name} />
          </div>
        </>
      )}
    </div>
  );
}
