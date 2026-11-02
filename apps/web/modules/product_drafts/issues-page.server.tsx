import "server-only"
import { redirect } from "next/navigation"
import { getCurrentUser } from "@/modules/auth/public.server"
import { apiGet } from "@/shared/api/request.server"
import { canAccessRoute } from "@/shared/access/permissions"
import { fetchPaginatedList, parsePagination } from "@/shared/pagination/fetch.server"
import { getT } from "@/shared/i18n/locale.server"
import { DRAFTS_ROUTE } from "./manifest"
import { issueMessages } from "./i18n"
import DraftIssues from "./ui/DraftIssues"

export type DraftIssuesPageProps = { searchParams: Promise<{
  source_key?: string; cursor?: string; direction?: string; seq?: string
}> }

export async function generateMetadata() {
  return { title: (await getT(issueMessages))("title") }
}

export default async function DraftIssuesPage({ searchParams }: DraftIssuesPageProps) {
  const user = await getCurrentUser()
  if (!canAccessRoute(user.data?.permissions ?? [], DRAFTS_ROUTE)) redirect("/products")
  const params = await searchParams
  const pagination = parsePagination(params)
  const t = await getT(issueMessages)
  const query = params.source_key ? { source_key: params.source_key } : {}
  const issues = await fetchPaginatedList({ url: "/product-drafts/issues", ...pagination,
    limit: 20, query, errorFallback: t("failed") })
  const sources = [...new Set(issues.items.map((issue) => issue.source_key))]
  const drafts = await Promise.all(sources.map((source_key) =>
    apiGet({ url: "/product-drafts/", query: { source_key, limit: 100 } })))
  const targets = drafts.flatMap((result) => result.status === "success" ? result.data.list_data : [])
  return <DraftIssues issues={issues} drafts={targets}
    source={params.source_key} seq={pagination.seq}
    error={drafts.some((result) => result.status !== "success") ? t("failed") : ""} />
}
