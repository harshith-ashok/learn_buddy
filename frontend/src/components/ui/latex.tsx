import katex from "katex";

interface LatexProps {
  expr: string;
  display?: boolean;
  className?: string;
}

/**
 * Renders a bare LaTeX expression (no `$`/`\[` delimiters expected) via
 * KaTeX. Pure string rendering — no DOM APIs — so this needs no "use
 * client" and can't hydration-mismatch. Falls back to the raw expression,
 * visibly marked, if it doesn't parse (model output isn't guaranteed
 * valid LaTeX) rather than throwing and taking the page down with it.
 */
export function Latex({ expr, display = false, className = "" }: LatexProps) {
  let html: string;
  try {
    html = katex.renderToString(expr, { displayMode: display, throwOnError: true, strict: "ignore" });
  } catch {
    return (
      <code className={`rounded-control bg-surface-sunken px-1.5 py-0.5 font-mono text-[0.9em] text-rust ${className}`}>
        {expr}
      </code>
    );
  }
  // katex's own sanitized output, not user HTML.
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
