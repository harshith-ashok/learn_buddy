import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workedAnswerApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useWorkedAnswerHistory(studyKitId: string, problemIndex: number) {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["worked-answer", studyKitId, problemIndex],
    queryFn: () => workedAnswerApi.listForProblem(studyKitId, problemIndex),
    enabled: isAuthenticated && !isLoading,
  });
}

export function useGradeWorkedAnswer(studyKitId: string, problemIndex: number) {
  const queryClient = useQueryClient();
  const { studentId } = useAuth();
  return useMutation({
    mutationFn: (work: string) => workedAnswerApi.grade(studyKitId, problemIndex, work),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["worked-answer", studyKitId, problemIndex] });
      queryClient.invalidateQueries({ queryKey: ["progress", studentId] });
      queryClient.invalidateQueries({ queryKey: ["recommendation-next"] });
    },
  });
}
