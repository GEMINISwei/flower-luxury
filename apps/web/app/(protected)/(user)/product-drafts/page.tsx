import { DraftsPage, generateDraftsMetadata, type DraftsPageProps } from "@/modules/product_drafts/public.server"

export const generateMetadata = generateDraftsMetadata
export default function Page(props: DraftsPageProps) {
  return <DraftsPage {...props} />
}
