import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { studyKitApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { StudyKitType } from "@/lib/types";

export function useStudyKitsForTopic(topicId: string) {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["study-kits", topicId],
    queryFn: () => studyKitApi.listForTopic(topicId),
    enabled: isAuthenticated && !isLoading,
  });
}

export function useGenerateStudyKit(topicId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (kitType: StudyKitType) => studyKitApi.generate(topicId, kitType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["study-kits", topicId] });
    },
  });
}
