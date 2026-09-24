import { AuthGuard } from "@/components/auth-guard";
import { TopicPageContent } from "@/components/topic/topic-page-content";

export default async function StudyKitPage({
  params,
}: {
  params: Promise<{ topicId: string }>;
}) {
  const { topicId } = await params;

  return (
    <AuthGuard>
      <TopicPageContent topicId={topicId} />
    </AuthGuard>
  );
}
