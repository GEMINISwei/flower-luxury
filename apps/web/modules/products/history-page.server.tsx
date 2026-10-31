import "server-only"
import { notFound } from "next/navigation"
import { apiGet } from "@/shared/api/request.server"
import { getT } from "@/shared/i18n/locale.server"
import { Container, ErrorState, FormPageShell } from "@/shared/ui"
import { productMessages } from "./i18n"
import SaleHistory from "./ui/SaleHistory"
import StatusTimeline from "./ui/StatusTimeline"
import styles from "./ui/product-detail.module.css"

export type ProductHistoryPageProps = { params: Promise<{ id: string }> }

export async function generateMetadata() {
  return { title: (await getT(productMessages))("productHistory") }
}

export default async function ProductHistoryPage({ params }: ProductHistoryPageProps) {
  const { id } = await params
  const product = await apiGet({ url: "/products/{id}", params: { id } })
  if (product.code === 404 || product.code === 422) notFound()
  const t = await getT(productMessages)
  if (product.status !== "success") {
    return <Container padded><ErrorState>{t("failed")}</ErrorState></Container>
  }
  const [histories, sales] = await Promise.all([
    apiGet({ url: "/products/{id}/history", params: { id } }),
    apiGet({ url: "/products/{id}/sales", params: { id } }),
  ])
  if (histories.status !== "success" || sales.status !== "success") {
    return <Container padded><ErrorState>{t("failed")}</ErrorState></Container>
  }
  return <FormPageShell title={t("productHistory")} actions={null}
    backHref={`/products/${id}`} backLabel={t("backToDetail")}>
    <div className={styles.stack}>
      <div><h2>{product.data.name}</h2><p>{product.data.sku}</p></div>
      <SaleHistory sales={sales.data.list_data} />
      <StatusTimeline histories={histories.data.list_data} createdAt={product.data.created_at} />
    </div>
  </FormPageShell>
}
