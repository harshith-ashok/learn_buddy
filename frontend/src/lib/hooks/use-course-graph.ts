import { useQuery } from "@tanstack/react-query";
import { graphApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useCourseGraph(courseId: string | undefined) {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["course-graph", courseId],
    queryFn: () => graphApi.getCourseGraph(courseId as string),
    enabled: isAuthenticated && !isLoading && courseId !== undefined,
  });
}
