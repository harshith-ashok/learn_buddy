"use client";

import { useState } from "react";
import type { FlashcardsContent } from "@/lib/types";

function Flashcard({ question, answer }: { question: string; answer: string }) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setIsFlipped((flipped) => !flipped)}
      className="h-40 w-full text-left perspective-distant"
      aria-label={isFlipped ? "Show question" : "Show answer"}
    >
      <div
        className="relative h-full w-full transform-3d transition-transform duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
        style={{ transform: isFlipped ? "rotateY(180deg)" : undefined }}
      >
        <div className="absolute inset-0 flex items-center justify-center rounded-card border border-border bg-surface-raised p-6 text-center text-base text-ink backface-hidden">
          {question}
        </div>
        <div
          className="absolute inset-0 flex items-center justify-center rounded-card border border-moss/30 bg-moss-tint p-6 text-center text-base text-moss backface-hidden"
          style={{ transform: "rotateY(180deg)" }}
        >
          {answer}
        </div>
      </div>
    </button>
  );
}

export function FlashcardsView({ content }: { content: FlashcardsContent }) {
  return (
    <div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {content.cards.map((card, index) => (
          <Flashcard key={index} question={card.question} answer={card.answer} />
        ))}
      </div>
      <p className="mt-3 text-xs text-ink-faint">
        Click a card to flip it · {content.cards.length} cards in this set
      </p>
    </div>
  );
}
