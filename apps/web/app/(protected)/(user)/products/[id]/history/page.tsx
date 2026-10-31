import {
  ProductHistoryPage, generateProductHistoryMetadata, type ProductHistoryPageProps,
} from "@/modules/products/public.server"

export const generateMetadata = generateProductHistoryMetadata

export default function Page(props: ProductHistoryPageProps) {
  return <ProductHistoryPage {...props} />
}
