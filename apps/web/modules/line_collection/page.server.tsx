import "server-only"
import { redirect } from "next/navigation"
import { getCurrentUser } from "@/modules/auth/public.server"
import { canAccessRoute } from "@/shared/access/permissions"
import { fetchPaginatedList, parsePagination } from "@/shared/pagination/fetch.server"
import { getT } from "@/shared/i18n/locale.server"
import { groupMessages } from "./i18n"
import { LINE_GROUPS_ROUTE } from "./manifest"
import GroupsView from "./ui/GroupsView"

export type GroupsPageProps = {
  searchParams: Promise<{ cursor?: string; direction?: string; seq?: string }>
}
export async function generateMetadata() {
  return { title: (await getT(groupMessages))("title") }
}
export default async function GroupsPage({ searchParams }: GroupsPageProps) {
  const user = await getCurrentUser()
  if (!canAccessRoute(user.data?.permissions ?? [], LINE_GROUPS_ROUTE)) redirect("/products")
  const pagination = parsePagination(await searchParams)
  const t = await getT(groupMessages)
  const result = await fetchPaginatedList({ url: "/line/groups", ...pagination, limit: 20,
    errorFallback: t("failed") })
  return <GroupsView {...result} seq={pagination.seq} limit={20} />
}
