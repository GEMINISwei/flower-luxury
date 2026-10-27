import { VendorsPage, generateVendorsMetadata } from "@/modules/vendors/public.server"

export const generateMetadata = generateVendorsMetadata

export default function Page() {
  return <VendorsPage />
}
