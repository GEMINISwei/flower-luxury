import { DraftIssuesPage, generateDraftIssuesMetadata,
  type DraftIssuesPageProps } from "@/modules/product_drafts/public.server"

export const generateMetadata = generateDraftIssuesMetadata
export default function Page(props: DraftIssuesPageProps) {
  return <DraftIssuesPage {...props} />
}
