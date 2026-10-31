"use client"

import { PageHeader } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { settingsMessages } from "../i18n"
import PasswordSettings from "./PasswordSettings"
import ProfileSettings from "./ProfileSettings"
import styles from "./settings.module.css"

export default function SettingsView({ nickname }: { nickname: string }) {
  const t = useT(settingsMessages)

  return (
    <div className={styles.page}>
      <PageHeader title={t("pageTitle")} />
      <div className={styles.content}>
        <ProfileSettings nickname={nickname} />
        <PasswordSettings />
      </div>
    </div>
  )
}
