import "server-only"
import { redirect } from "next/navigation"
import { getCurrentUser } from "@/modules/auth/public.server"
import { apiGet } from "@/shared/api/request.server"
import { canAccessRoute } from "@/shared/access/permissions"
import { fetchPaginatedList, parsePagination } from "@/shared/pagination/fetch.server"
import { getT } from "@/shared/i18n/locale.server"
import { DRAFTS_ROUTE } from "./manifest"
import { draftMessages } from "./i18n"
import DraftsView from "./ui/DraftsView"

export type DraftsPageProps = { searchParams: Promise<{
  cursor?: string; direction?: string; seq?: string; source_key?: string; view?: string
}> }
export async function generateMetadata() {
  return { title: (await getT(draftMessages))("title") }
}
export default async function DraftsPage({ searchParams }: DraftsPageProps) {
  const user = await getCurrentUser()
  if (!canAccessRoute(user.data?.permissions ?? [], DRAFTS_ROUTE)) redirect("/products")
  const params = await searchParams
  const pagination = parsePagination(params)
  const t = await getT(draftMessages)
  const unassigned = params.view === "messages"
  const options = { ...pagination, limit: 20, errorFallback: t("failed"),
    query: params.source_key ? { source_key: params.source_key } : {} }
  const [sources, drafts, messages, legacy] = await Promise.all([
    apiGet({ url: "/line/sources" }),
    unassigned ? null : fetchPaginatedList({ url: "/product-drafts/", ...options }),
    unassigned ? fetchPaginatedList({ url: "/product-drafts/messages", ...options }) : null,
    unassigned ? null : fetchPaginatedList({ url: "/product-drafts/messages", limit: 1, direction: "next",
      query: options.query, errorFallback: t("failed") }),
  ])
  return <DraftsView drafts={drafts} messages={messages} unassigned={unassigned}
    sources={sources.status === "success" ? sources.data.list_data : []}
    source={params.source_key ?? ""} seq={pagination.seq} limit={20}
    hasLegacy={Boolean(legacy?.meta.totalCount)}
    sourceError={sources.status === "success" ? (legacy?.errorMessage ?? "") : t("failed")} />
}
