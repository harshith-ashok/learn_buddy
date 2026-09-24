import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { feynmanApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useFeynmanHistory(topicId: string) {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["feynman", topicId],
    queryFn: () => feynmanApi.listForTopic(topicId),
    enabled: isAuthenticated && !isLoading,
  });
}

export function useGradeFeynman(topicId: string) {
  const queryClient = useQueryClient();
  const { studentId } = useAuth();
  return useMutation({
    mutationFn: (explanation: string) => feynmanApi.grade(topicId, explanation),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feynman", topicId] });
      queryClient.invalidateQueries({ queryKey: ["progress", studentId] });
      queryClient.invalidateQueries({ queryKey: ["recommendation-next"] });
    },
  });
}
