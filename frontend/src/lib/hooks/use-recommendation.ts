import { useQuery } from "@tanstack/react-query";
import { recommendationApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export function useRecommendation() {
  const { isAuthenticated, isLoading } = useAuth();
  return useQuery({
    queryKey: ["recommendation-next"],
    queryFn: recommendationApi.getNext,
    enabled: isAuthenticated && !isLoading,
  });
}
