"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAskChat, useChatHistory } from "@/lib/hooks/use-chat";
import type { ChatMessageOut } from "@/lib/types";
import { AgentActivity } from "@/components/topic/agent-activity";
import { ErrorBanner } from "@/components/ui/error-banner";
import { Spinner } from "@/components/ui/spinner";

const ASK_STAGES = [
  { label: "RETRIEVING TOPIC CONTEXT" },
  { label: "CHECKING COVERAGE" },
  { label: "GENERATING ANSWER" },
  { label: "FINDING RELATED TOPICS" },
];

function MessageRow({ message }: { message: ChatMessageOut }) {
  const isUser = message.role === "user";
  const isRefusal = !isUser && !message.covered;

  return (
    <div
      className={`border-b border-border-soft py-4 last:border-b-0 ${isRefusal ? "border-l-2 border-l-rust pl-4" : ""}`}
    >
      <div className="mb-1.5 flex items-center gap-2">
        <span
          className={`h-[6px] w-[6px] rounded-full ${isUser ? "bg-ink-faint" : isRefusal ? "bg-rust" : "bg-moss"}`}
        />
        <span className="font-mono text-[11px] tracking-wide text-ink-faint">
          {isUser ? "YOU" : isRefusal ? "NOT COVERED" : "ANSWER"}
        </span>
      </div>
      <p className={`text-[14px] leading-relaxed ${isRefusal ? "text-ink-muted" : "text-ink"}`}>
        {message.content}
      </p>

      {!isUser && (message.source_chunk_ids.length > 0 || message.related_topics.length > 0) && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {message.source_chunk_ids.length > 0 && (
            <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10.5px] text-ink-faint">
              {message.source_chunk_ids.length} source{message.source_chunk_ids.length > 1 ? "s" : ""}
            </span>
          )}
          {message.related_topics.map((related) => (
            <Link
              key={related.topic_id}
              href={`/study-kit/${related.topic_id}`}
              className="rounded-full border border-brand-500/40 px-2.5 py-1 font-mono text-[10.5px] text-brand-500 transition-colors hover:border-brand-500 hover:bg-brand-500/10"
            >
              see also: {related.topic_name}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function TopicChat({ topicId, topicName }: { topicId: string; topicName: string }) {
  const history = useChatHistory(topicId);
  const ask = useAskChat(topicId);
  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages = history.data ?? [];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages.length, pendingQuestion]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || ask.isPending) return;
    setPendingQuestion(message);
    setDraft("");
    ask.mutate(message, { onSettled: () => setPendingQuestion(null) });
  }

  return (
    <div className="mt-3">
      <div className="mb-4.5 text-[11px] tracking-[0.08em] text-ink-faint">ASK ABOUT THIS TOPIC</div>

      <div
        ref={scrollRef}
        className="max-h-[420px] overflow-y-auto rounded-card border border-border bg-surface-raised px-5"
      >
        {history.isPending && (
          <div className="py-6">
            <Spinner label="Loading conversation…" />
          </div>
        )}
        {history.isError && (
          <div className="py-4">
            <ErrorBanner error={history.error} />
          </div>
        )}
        {history.data && messages.length === 0 && !pendingQuestion && (
          <p className="py-6 text-[13px] text-ink-faint">
            Ask anything about <span className="text-ink-muted">{topicName}</span> — answers are grounded
            only in this topic&apos;s own material.
          </p>
        )}
        {messages.map((message) => (
          <MessageRow key={message.id} message={message} />
        ))}
        {pendingQuestion && (
          <div className="border-b border-border-soft py-4 last:border-b-0">
            <div className="mb-1.5 flex items-center gap-2">
              <span className="h-[6px] w-[6px] rounded-full bg-ink-faint" />
              <span className="font-mono text-[11px] tracking-wide text-ink-faint">YOU</span>
            </div>
            <p className="text-[14px] leading-relaxed text-ink">{pendingQuestion}</p>
          </div>
        )}
        {ask.isPending && (
          <div className="py-4">
            <AgentActivity stages={ASK_STAGES} active />
          </div>
        )}
        {ask.isError && (
          <div className="py-4">
            <ErrorBanner error={ask.error} />
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2.5">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={`Ask a question about ${topicName}…`}
          disabled={ask.isPending}
          maxLength={2000}
          className="flex-1 rounded-control border border-border bg-transparent px-3.5 py-2.5 text-[13.5px] text-ink outline-none focus:border-brand-500 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={ask.isPending || draft.trim().length === 0}
          className="rounded-control bg-brand-500 px-5 py-2.5 text-[13.5px] font-semibold text-surface transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-200 disabled:text-ink-faint"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
