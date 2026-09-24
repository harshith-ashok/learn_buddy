import { AuthGuard } from "@/components/auth-guard";
import { UploadDropzone } from "@/components/upload-dropzone";
import { DocumentList } from "@/components/document-list";

export default function UploadPage() {
  return (
    <AuthGuard>
      <div className="mx-auto flex w-full max-w-180 flex-col gap-8 px-8 pb-32 pt-10">
        <div className="max-w-[56ch]">
          <span className="mb-2.5 block text-[11px] tracking-[0.08em] text-ink-faint">
            ADD MATERIAL
          </span>
          <h2 className="mb-2.5 text-[28px] font-semibold text-ink">Upload documents</h2>
          <p className="text-sm leading-relaxed text-ink-muted">
            Add a syllabus, lecture notes, or slides. We&apos;ll parse them into topics and add
            them to your ledger.
          </p>
        </div>
        <UploadDropzone />
        <div>
          <span className="mb-3.5 block text-[11px] tracking-[0.08em] text-ink-faint">
            YOUR DOCUMENTS
          </span>
          <DocumentList />
        </div>
      </div>
    </AuthGuard>
  );
}
