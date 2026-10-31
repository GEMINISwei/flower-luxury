"use client"

import Image from "next/image"
import { Shield } from "lucide-react"
import { ICON_SIZE } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { usePublicConfig } from "@/shared/runtime/context"
import { authMessages } from "../i18n"
import styles from "./auth.module.css"

export function AuthBrand() {
  const { systemName } = usePublicConfig()
  return <>
    <Image src="/logo.png" alt="" width={150} height={150} className={styles.emblem} priority />
    <h1 className={styles.appName}>{systemName}</h1>
    <div className={styles.brandDivider} aria-hidden="true"><span>◇</span></div>
  </>
}

export function AuthSecurityNote() {
  const t = useT(authMessages)
  return <>
    <div className={styles.divider} aria-hidden="true"><span>◇</span></div>
    <div className={styles.securityNote}>
      <Shield size={ICON_SIZE.sm} color="var(--color-primary)" />
      <span>{t("securityNote")}</span>
    </div>
  </>
}
