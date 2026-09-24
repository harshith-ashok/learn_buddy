import { useQuery } from "@tanstack/react-query";
import { progressApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useProgress() {
  const { studentId, isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["progress", studentId],
    queryFn: () => progressApi.get(studentId as string),
    enabled: isAuthenticated && !isLoading && studentId !== null,
  });
}
