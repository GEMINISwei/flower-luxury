import "server-only"
import Link from "next/link"
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
import { draftQueueHref, draftStage } from "./capabilities"

export type DraftDetailPageProps = { params: Promise<{ id: string }>;
  searchParams: Promise<{ source_key?: string; created?: string }> }
export async function generateMetadata() {
  return { title: (await getT(draftMessages))("detail") }
}
export default async function DraftDetailPage({ params, searchParams }: DraftDetailPageProps) {
  const user = await getCurrentUser()
  if (!canAccessRoute(user.data?.permissions ?? [], DRAFTS_ROUTE)) redirect("/products")
  const { id } = await params
  const query = await searchParams
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
  const stage = draftStage(draft.data)
  if (stage !== "waiting") return <Container padded>
    <p role="status">{t(stage)} — {t("blockedHint")}</p>
    <Link href={draftQueueHref(undefined, query.source_key)}>{t("back")}</Link>
    {stage === "needsConfirmation" && <p><Link
      href={`/product-drafts/issues?source_key=${encodeURIComponent(draft.data.source_key)}`}>
      {t("reviewIssues")}</Link></p>}
  </Container>
  return <DraftDetail key={id} initial={draft.data} brands={brands.data.list_data}
    sources={sources.data.list_data} vendors={vendors.data.list_data}
    scope={query.source_key} created={query.created} />
}
