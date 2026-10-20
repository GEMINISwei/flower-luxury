import { NewProductPage, generateNewProductMetadata } from "@/modules/products/public.server"

export const generateMetadata = generateNewProductMetadata

export default function Page() {
  return <NewProductPage />
}
