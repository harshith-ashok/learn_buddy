import { type ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-brand-500 text-surface hover:bg-brand-700 disabled:bg-brand-200 disabled:text-ink-faint",
  secondary:
    "bg-transparent text-ink border border-border hover:border-ink-muted disabled:text-ink-faint disabled:border-border",
  ghost: "text-ink-muted hover:text-ink disabled:text-ink-faint",
  danger: "bg-danger text-surface hover:opacity-90 disabled:opacity-50",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className = "", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`group inline-flex items-center justify-center gap-2 rounded-control px-4.5 py-3 text-[13.5px] font-semibold transition-all duration-150 ease-out hover:translate-x-0.5 disabled:cursor-not-allowed disabled:translate-x-0 ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    />
  );
});
