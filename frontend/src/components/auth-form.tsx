"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { ErrorBanner } from "@/components/ui/error-banner";

interface AuthFormProps {
  mode: "login" | "register";
}

export function AuthForm({ mode }: AuthFormProps) {
  const { login, register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName);
      }
      router.replace("/dashboard");
    } catch (submitError) {
      setError(submitError);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="relative flex flex-1 items-center justify-center px-8 py-16">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-70 opacity-60 mask-[linear-gradient(to_bottom,black,transparent)] bg-[radial-gradient(circle_at_1.5px_1.5px,var(--color-border-soft)_1.2px,transparent_0)] bg-size-[22px_22px]"
      />
      <div className="relative w-full max-w-sm">
        <span className="mb-2 block font-mono text-xs tracking-[0.06em] text-ink-muted">
          LEARN BUDDY
        </span>
        <h1 className="mb-7 text-[28px] font-semibold text-ink">
          {mode === "login" ? "Sign in" : "Create your account"}
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === "register" && (
            <label className="flex flex-col gap-1.5 text-[13px] text-ink-muted">
              Full name
              <input
                required
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className="rounded-control border border-border bg-transparent px-3 py-2.5 text-ink outline-none focus:border-brand-500"
              />
            </label>
          )}
          <label className="flex flex-col gap-1.5 text-[13px] text-ink-muted">
            Email
            <input
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded-control border border-border bg-transparent px-3 py-2.5 text-ink outline-none focus:border-brand-500"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-[13px] text-ink-muted">
            Password
            <input
              required
              type="password"
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-control border border-border bg-transparent px-3 py-2.5 text-ink outline-none focus:border-brand-500"
            />
          </label>

          {error !== null && <ErrorBanner error={error} />}

          <Button type="submit" disabled={isSubmitting} className="mt-2">
            {isSubmitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className="mt-7 text-center text-[13px] text-ink-muted">
          {mode === "login" ? (
            <>
              Need an account?{" "}
              <Link href="/register" className="font-medium text-brand-500 hover:underline">
                Register
              </Link>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <Link href="/login" className="font-medium text-brand-500 hover:underline">
                Sign in
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
