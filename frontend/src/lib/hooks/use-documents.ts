import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const IN_PROGRESS_STATUSES = new Set(["pending", "processing"]);

export function useDocuments() {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["documents"],
    queryFn: documentsApi.list,
    enabled: isAuthenticated && !isLoading,
    // Poll while anything is still ingesting, to show progress; stop once
    // every document has settled into done/failed.
    refetchInterval: (query) => {
      const documents = query.state.data;
      const stillIngesting = documents?.some((doc) => IN_PROGRESS_STATUSES.has(doc.status));
      return stillIngesting ? 2000 : false;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, examDate }: { file: File; examDate?: string }) =>
      documentsApi.upload(file, examDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
