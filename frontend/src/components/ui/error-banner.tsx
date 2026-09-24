import { ApiError } from "@/lib/api";

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export function ErrorBanner({ error }: { error: unknown }) {
  return (
    <div
      role="alert"
      className="rounded-control border-l-2 border-danger bg-danger-surface px-4 py-3 text-sm text-danger"
    >
      {errorMessage(error)}
    </div>
  );
}
