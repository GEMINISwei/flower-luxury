import "server-only"
import { apiGet } from "@/shared/api/request.server"
import { getApiResponseErrorMessage } from "@/shared/api/error"
import { getT } from "@/shared/i18n/locale.server"
import { registrationMessages } from "./i18n"
import RegistrationSettings from "./ui/RegistrationSettings"

export async function generateMetadata() {
  return { title: (await getT(registrationMessages))("settingsTitle") }
}

export default async function RegistrationPage() {
  const t = await getT(registrationMessages)
  const result = await apiGet({ url: "/registration/settings" })
  return <RegistrationSettings
    configured={result.status === "success" ? result.data.configured : false}
    errorMessage={result.status === "success"
      ? "" : getApiResponseErrorMessage(result, t("settingsFailed"))}
  />
}
