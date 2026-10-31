import "server-only"
import { getCurrentUser } from "@/modules/auth/public.server"
import { getT } from "@/shared/i18n/locale.server"
import { settingsMessages } from "./i18n"
import SettingsView from "./ui/SettingsView"

export async function generateMetadata() {
  return { title: (await getT(settingsMessages))("pageTitle") }
}

export default async function SettingsPage() {
  const { data } = await getCurrentUser()
  return <SettingsView nickname={data?.nickname ?? ""} />
}
