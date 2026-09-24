"use client";

import { useState } from "react";
import { useGenerateStudyKit, useStudyKitsForTopic } from "@/lib/hooks/use-study-kit";
import { isStudyKit } from "@/lib/types";
import type {
  FlashcardsContent,
  ProblemGuideContent,
  QuizContent,
  StudyKitOut,
  StudyKitType,
  SummaryContent,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";
import { SummaryView } from "@/components/study-kit/summary-view";
import { FlashcardsView } from "@/components/study-kit/flashcards-view";
import { QuizView } from "@/components/study-kit/quiz-view";
import { ProblemGuideView } from "@/components/study-kit/problem-guide-view";
import { AgentActivity } from "@/components/topic/agent-activity";

const KIT_TYPES: { value: StudyKitType; label: string }[] = [
  { value: "summary", label: "Summary" },
  { value: "flashcards", label: "Flashcards" },
  { value: "quiz", label: "Quiz" },
  { value: "problem_guide", label: "Problem guide" },
];

// Mirrors the LangGraph nodes a `generate_study_kit` request actually runs
// through (wiki/agent-design.md) — classify -> retrieve+guardrail ->
// generate -> persist. The API returns one response with no intermediate
// progress, so this is a simulated sequence, not a live trace.
function stagesForKit(kitType: StudyKitType) {
  const label = KIT_TYPES.find((type) => type.value === kitType)?.label ?? "kit";
  return [
    { label: "CLASSIFYING INTENT" },
    { label: "RETRIEVING CONTEXT" },
    { label: "CHECKING COVERAGE" },
    { label: `GENERATING ${label.toUpperCase()}` },
    { label: "SAVING STUDY KIT" },
  ];
}

function KitContent({ kit, topicId }: { kit: StudyKitOut; topicId: string }) {
  switch (kit.kit_type) {
    case "summary":
      return <SummaryView content={kit.content as SummaryContent} />;
    case "flashcards":
      return <FlashcardsView content={kit.content as FlashcardsContent} />;
    case "quiz":
      return <QuizView content={kit.content as QuizContent} topicId={topicId} studyKitId={kit.id} />;
    case "problem_guide":
      return <ProblemGuideView content={kit.content as ProblemGuideContent} studyKitId={kit.id} />;
  }
}

export function KitSection({ topicId }: { topicId: string }) {
  const [kitType, setKitType] = useState<StudyKitType>("summary");
  const { data: existingKits, isPending: isLoadingKits } = useStudyKitsForTopic(topicId);
  const generate = useGenerateStudyKit(topicId);

  const existingKit = existingKits?.find((kit) => kit.kit_type === kitType);
  // A freshly generated kit for the *current* tab shows immediately,
  // without waiting for the kit list to refetch.
  const freshKit =
    generate.data && isStudyKit(generate.data) && generate.data.kit_type === kitType
      ? generate.data
      : undefined;
  const activeKit = freshKit ?? existingKit;
  const notCovered = generate.data && !isStudyKit(generate.data) ? generate.data : undefined;
  const activeLabel = KIT_TYPES.find((type) => type.value === kitType)?.label.toLowerCase();

  function handleTabChange(next: StudyKitType) {
    setKitType(next);
    generate.reset();
  }

  return (
    <div className="mt-3">
      <div className="mb-4.5 text-[11px] tracking-[0.08em] text-ink-faint">
        GENERATE A STUDY KIT
      </div>
      <div role="tablist" className="flex gap-7 overflow-x-auto border-b border-border">
        {KIT_TYPES.map((type) => (
          <button
            key={type.value}
            type="button"
            role="tab"
            aria-selected={kitType === type.value}
            onClick={() => handleTabChange(type.value)}
            className={`whitespace-nowrap border-b-2 pb-4 pt-1 text-[13.5px] font-semibold transition-colors ${
              kitType === type.value
                ? "border-brand-500 text-ink"
                : "border-transparent text-ink-faint hover:text-ink-muted"
            }`}
          >
            {type.label}
          </button>
        ))}
      </div>

      <div className="min-h-[200px] pb-2 pt-8">
        {isLoadingKits ? (
          <Spinner label="Loading study kits…" />
        ) : (
          <div className="flex flex-col gap-5">
            {generate.isError && <ErrorBanner error={generate.error} />}
            {notCovered && <p className="text-sm text-ink-muted">{notCovered.message}</p>}
            {activeKit && <KitContent kit={activeKit} topicId={topicId} />}

            <AgentActivity stages={stagesForKit(kitType)} active={generate.isPending} />

            <Button
              variant={activeKit ? "secondary" : "primary"}
              onClick={() => generate.mutate(kitType)}
              disabled={generate.isPending}
              className="self-start"
            >
              {generate.isPending
                ? "Working…"
                : activeKit
                  ? "Regenerate"
                  : `Generate ${activeLabel}`}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
