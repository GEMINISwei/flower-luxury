import "server-only"
import { apiGet } from "@/shared/api/request.server"
import { getApiResponseErrorMessage } from "@/shared/api/error"
import { getT } from "@/shared/i18n/locale.server"
import { vendorMessages } from "./i18n"
import VendorsView from "./ui/VendorsView"

export function getVendorOptions() {
  return apiGet({ url: "/vendors/", query: { include_inactive: true } })
}

export async function generateMetadata() {
  return { title: (await getT(vendorMessages))("title") }
}

export default async function VendorsPage() {
  const t = await getT(vendorMessages)
  const result = await getVendorOptions()
  return <VendorsView vendors={result.status === "success" ? result.data.list_data : []}
    errorMessage={result.status === "success" ? "" : getApiResponseErrorMessage(result, t("failed"))} />
}
