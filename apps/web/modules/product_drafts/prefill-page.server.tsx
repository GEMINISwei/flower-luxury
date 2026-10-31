import "server-only"
import { apiGet } from "@/shared/api/request.server"
import { getT } from "@/shared/i18n/locale.server"
import { prefillMessages } from "./i18n"
import PrefillSettings from "./ui/PrefillSettings"

export async function generateMetadata() {
  return { title: (await getT(prefillMessages))("title") }
}
export default async function PrefillSettingsPage() {
  const result = await apiGet({ url: "/draft-prefill/settings" })
  const t = await getT(prefillMessages)
  return <PrefillSettings initial={result.status === "success" ? result.data : null}
    errorMessage={result.status === "success" ? "" : t("failed")} />
}
