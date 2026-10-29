import { DraftDetailPage, generateDraftDetailMetadata, type DraftDetailPageProps } from "@/modules/product_drafts/public.server"

export const generateMetadata = generateDraftDetailMetadata
export default function Page(props: DraftDetailPageProps) {
  return <DraftDetailPage {...props} />
}
