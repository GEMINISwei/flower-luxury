import { BrandsPage, generateBrandsMetadata } from "@/modules/brands/public.server"

export const generateMetadata = generateBrandsMetadata

export default function Page() {
  return <BrandsPage />
}
