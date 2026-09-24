import { useMutation, useQueryClient } from "@tanstack/react-query";
import { quizApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { QuizAnswer } from "@/lib/types";

export function useSubmitQuiz(topicId: string, studyKitId: string) {
  const queryClient = useQueryClient();
  const { studentId } = useAuth();
  return useMutation({
    mutationFn: (answers: QuizAnswer[]) => quizApi.submit(topicId, studyKitId, answers),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["progress", studentId] });
      queryClient.invalidateQueries({ queryKey: ["recommendation-next"] });
    },
  });
}
