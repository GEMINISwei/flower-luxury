"use client"

import { useRef } from "react"
import { Camera, Upload } from "lucide-react"
import { Button, ICON_SIZE } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { productMessages } from "../i18n"
import styles from "./photo-picker.module.css"

export default function PhotoPicker({ disabled, onSelect, compact = false }: {
  disabled: boolean; onSelect: (files: File[]) => void; compact?: boolean
}) {
  const t = useT(productMessages)
  const library = useRef<HTMLInputElement>(null)
  const camera = useRef<HTMLInputElement>(null)
  function select(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ""
    onSelect(files)
  }
  return <div className={`${styles.actions} ${compact ? styles.compact : ""}`}>
    <Button variant="outlined" disabled={disabled}
      icon={<Upload size={ICON_SIZE.sm} aria-hidden />} onClick={() => library.current?.click()}>
      {t("upload")}</Button>
    <Button variant="outlined" disabled={disabled}
      icon={<Camera size={ICON_SIZE.sm} aria-hidden />} onClick={() => camera.current?.click()}>
      {t("takePhoto")}</Button>
    <input ref={library} type="file" multiple hidden aria-label={t("upload")}
      accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
      disabled={disabled} onChange={select} />
    <input ref={camera} type="file" hidden aria-label={t("takePhoto")}
      accept="image/*" capture="environment" disabled={disabled} onChange={select} />
  </div>
}
