import { ProductsPage, generateProductsMetadata, type ProductsPageProps } from "@/modules/products/public.server"

export const generateMetadata = generateProductsMetadata

export default function Page(props: ProductsPageProps) {
  return <ProductsPage {...props} />
}
