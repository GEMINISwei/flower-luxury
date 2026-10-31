import "server-only"
import { notFound, redirect } from "next/navigation"
import { getCurrentUser } from "@/modules/auth/public.server"
import { getBrandOptions } from "@/modules/brands/public.server"
import { getVendorOptions } from "@/modules/vendors/public.server"
import { apiGet } from "@/shared/api/request.server"
import { canAccessRoute } from "@/shared/access/permissions"
import { getT } from "@/shared/i18n/locale.server"
import { Container, ErrorState } from "@/shared/ui"
import { draftMessages } from "./i18n"
import { DRAFTS_ROUTE } from "./manifest"
import DraftDetail from "./ui/DraftDetail"

export type DraftDetailPageProps = { params: Promise<{ id: string }> }
export async function generateMetadata() {
  return { title: (await getT(draftMessages))("detail") }
}
export default async function DraftDetailPage({ params }: DraftDetailPageProps) {
  const user = await getCurrentUser()
  if (!canAccessRoute(user.data?.permissions ?? [], DRAFTS_ROUTE)) redirect("/products")
  const { id } = await params
  const [draft, brands, sources, vendors] = await Promise.all([
    apiGet({ url: "/product-drafts/{id}", params: { id } }), getBrandOptions(),
    apiGet({ url: "/line/sources" }),
    getVendorOptions(),
  ])
  if (draft.code === 404 || draft.code === 422) notFound()
  const t = await getT(draftMessages)
  if (draft.status !== "success" || brands.status !== "success" || sources.status !== "success"
      || vendors.status !== "success") {
    return <Container padded><ErrorState>{t("failed")}</ErrorState></Container>
  }
  return <DraftDetail key={id} initial={draft.data} brands={brands.data.list_data}
    sources={sources.data.list_data} vendors={vendors.data.list_data} />
}
