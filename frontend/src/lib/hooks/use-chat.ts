import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useChatHistory(topicId: string) {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["chat", topicId],
    queryFn: () => chatApi.listForTopic(topicId),
    enabled: isAuthenticated && !isLoading,
  });
}

export function useAskChat(topicId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (message: string) => chatApi.ask(topicId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat", topicId] });
    },
  });
}
