import "server-only"
import { notFound } from "next/navigation"
import { apiGet } from "@/shared/api/request.server"
import { getBrandOptions } from "@/modules/brands/public.server"
import { getVendorOptions } from "@/modules/vendors/public.server"
import { getT } from "@/shared/i18n/locale.server"
import { Container, ErrorState } from "@/shared/ui"
import { productMessages } from "./i18n"
import ProductDetail from "./ui/ProductDetail"

export type ProductDetailPageProps = { params: Promise<{ id: string }> }
export async function generateMetadata() {
  return { title: (await getT(productMessages))("detail") }
}
export default async function ProductDetailPage({ params }: ProductDetailPageProps) {
  const { id } = await params
  const product = await apiGet({ url: "/products/{id}", params: { id } })
  if (product.code === 404 || product.code === 422) notFound()
  const [brands, photos, vendors, quotes, sales] = await Promise.all([
    getBrandOptions(), apiGet({ url: "/products/{id}/photos", params: { id } }),
    getVendorOptions(), apiGet({ url: "/products/{id}/quotes", params: { id } }),
    apiGet({ url: "/products/{id}/sales", params: { id } }),
  ])
  const t = await getT(productMessages)
  if (product.status !== "success" || brands.status !== "success"
      || photos.status !== "success"
      || vendors.status !== "success" || quotes.status !== "success" || sales.status !== "success") {
    return <Container padded><ErrorState>{t("failed")}</ErrorState></Container>
  }
  return <ProductDetail product={product.data} brands={brands.data.list_data}
    photos={photos.data.list_data}
    vendors={vendors.data.list_data}
    quotes={quotes.data.list_data} sales={sales.data.list_data} />
}
