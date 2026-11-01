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
  cursor?: string; direction?: string; seq?: string; source_key?: string; created?: string;
  completed?: string
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
  const options = { ...pagination, limit: 20, errorFallback: t("failed"),
    query: params.source_key ? { source_key: params.source_key } : {} }
  const [sources, drafts, processing] = await Promise.all([
    apiGet({ url: "/line/sources" }),
    fetchPaginatedList({ url: "/product-drafts/", ...options }),
    apiGet({ url: "/product-drafts/processing", query: options.query }),
  ])
  return <DraftsView drafts={drafts}
    sources={sources.status === "success" ? sources.data.list_data : []}
    source={params.source_key ?? ""} seq={pagination.seq} limit={20}
    created={params.created} completed={params.completed === "1"}
    processing={processing.status === "success" && processing.data.processing}
    sourceError={sources.status === "success" && processing.status === "success" ? "" : t("failed")} />
}
