import { ProductDetailPage, generateProductDetailMetadata, type ProductDetailPageProps } from "@/modules/products/public.server"

export const generateMetadata = generateProductDetailMetadata

export default function Page(props: ProductDetailPageProps) {
  return <ProductDetailPage {...props} />
}
