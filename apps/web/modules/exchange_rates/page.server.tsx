import "server-only"
import { apiGet } from "@/shared/api/request.server"
import { getT } from "@/shared/i18n/locale.server"
import { exchangeMessages } from "./i18n"
import ExchangeSettings from "./ui/ExchangeSettings"

export async function generateMetadata() {
  return { title: (await getT(exchangeMessages))("title") }
}
export default async function ExchangePage() {
  const result = await apiGet({ url: "/exchange-rates/settings" })
  const t = await getT(exchangeMessages)
  return <ExchangeSettings settings={result.status === "success" ? result.data : null}
    errorMessage={result.status === "success" ? "" : t("failed")} />
}
