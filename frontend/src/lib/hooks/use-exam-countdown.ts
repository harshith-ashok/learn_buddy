import { useDocuments } from "@/lib/hooks/use-documents";

const MS_PER_DAY = 1000 * 60 * 60 * 24;

/** Days until the soonest upcoming `exam_date` across all of the student's documents, or null if none is set. */
export function useExamCountdown(): number | null {
  const { data: documents } = useDocuments();
  if (!documents) return null;

  const now = Date.now();
  const upcoming = documents
    .map((document) => document.exam_date)
    .filter((date): date is string => date !== null)
    .map((date) => new Date(date).getTime())
    .filter((time) => time >= now);

  if (upcoming.length === 0) return null;
  return Math.ceil((Math.min(...upcoming) - now) / MS_PER_DAY);
}
