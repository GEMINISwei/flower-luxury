import "server-only"
import { apiGet } from "@/shared/api/request.server"
import { getApiResponseErrorMessage } from "@/shared/api/error"
import { getT } from "@/shared/i18n/locale.server"
import { brandMessages } from "./i18n"
import BrandsView from "./ui/BrandsView"

export async function getBrandOptions() {
  return apiGet({ url: "/brands/", query: { include_inactive: true } })
}
export async function generateMetadata() {
  return { title: (await getT(brandMessages))("title") }
}
export default async function BrandsPage() {
  const t = await getT(brandMessages)
  const result = await getBrandOptions()
  return <BrandsView brands={result.status === "success" ? result.data.list_data : []}
    errorMessage={result.status === "success" ? "" : getApiResponseErrorMessage(result, t("failed"))} />
}
