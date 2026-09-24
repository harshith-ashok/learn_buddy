"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) router.replace("/dashboard");
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (isAuthenticated) return null;

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center gap-7 px-8 py-24 text-center">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-70 opacity-60 mask-[linear-gradient(to_bottom,black,transparent)] bg-[radial-gradient(circle_at_1.5px_1.5px,var(--color-border-soft)_1.2px,transparent_0)] bg-size-[22px_22px]"
      />
      <span className="font-mono text-xs tracking-[0.06em] text-ink-muted">LEARN BUDDY</span>
      <h1 className="text-5xl font-bold leading-[0.97] tracking-tight text-ink sm:text-[60px]">
        Study<br />
        <em className="font-semibold text-brand-500 italic">Ledger</em>
      </h1>
      <p className="max-w-md text-[15px] leading-relaxed text-ink-muted">
        Upload your course material, get a personalized study plan, and track your mastery topic
        by topic.
      </p>
      <div className="flex gap-3">
        <Link href="/login">
          <Button>Sign in</Button>
        </Link>
        <Link href="/register">
          <Button variant="secondary">Create an account</Button>
        </Link>
      </div>
    </div>
  );
}
