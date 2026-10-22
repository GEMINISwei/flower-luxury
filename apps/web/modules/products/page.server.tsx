import "server-only"
import { fetchPaginatedList, parsePagination } from "@/shared/pagination/fetch.server"
import { getBrandOptions } from "@/modules/brands/public.server"
import { getT } from "@/shared/i18n/locale.server"
import { productMessages } from "./i18n"
import ProductsView from "./ui/ProductsView"

export type ProductsPageProps = { searchParams?: Promise<Record<string, string>> }

export async function generateMetadata() {
  return { title: (await getT(productMessages))("title") }
}
export default async function ProductsPage({ searchParams }: ProductsPageProps) {
  const t = await getT(productMessages)
  const params = await searchParams
  const { cursor, direction, seq } = parsePagination(params)
  const fields = ["keyword", "brand_id", "category", "status", "color", "year"]
  const filters = Object.fromEntries(fields.map((key) => [key, params?.[key] ?? ""]))
  const query = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
  const [result, brands] = await Promise.all([
    fetchPaginatedList({ url: "/products/", cursor, direction, limit: 20, query,
      errorFallback: t("failed") }), getBrandOptions(),
  ])
  return <ProductsView products={result.items} filters={filters} meta={result.meta} seq={seq}
    brands={brands.status === "success" ? brands.data.list_data : []}
    errorMessage={result.errorMessage || (brands.status === "success" ? "" : t("failed"))} />
}
