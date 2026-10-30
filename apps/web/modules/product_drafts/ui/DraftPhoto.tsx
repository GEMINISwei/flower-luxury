"use client"
import Image from "next/image"
import { ImageIcon } from "lucide-react"
import { Button, Flex, StatusBadge } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ApiResponse } from "@/shared/api/contract"
import { setDraftMainPhoto } from "../actions"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"
import styles from "./drafts.module.css"

export default function DraftPhoto({ draft, photo, disabled, mutate, onRemove }: {
  draft: DraftInfo; photo: DraftInfo["photos"][number]; disabled: boolean;
  mutate: (run: () => Promise<ApiResponse<DraftInfo>>) => void; onRemove: (id: string) => void
}) {
  const t = useT(draftMessages)
  return <article data-testid="draft-photo" className={styles.photo} data-main={photo.is_main}>
    {photo.url ? <a href={photo.url} target="_blank" rel="noreferrer"
      aria-label={t("preview")} className={styles.photoFrame}>
      <Image unoptimized src={photo.url} width={480} height={480}
        alt={t("preview")} className={styles.thumbnail} /></a>
      : <div className={styles.emptyPhoto}><ImageIcon className={styles.emptyIcon} aria-hidden="true" />
        <p>{t(photo.status === "failed" ? "failedPhoto" : photo.status)}</p></div>}
    <div className={styles.photoBody}>
      <div className={styles.sectionHeader}>
        <Flex gap={2} className={styles.meta}>
          <StatusBadge label={t(photo.status === "failed" ? "failedPhoto" : photo.status)}
            variant="muted" />
          {photo.is_main && <StatusBadge label={t("main")} variant="success" />}
        </Flex>
        {photo.download_url && <a href={photo.download_url}>{t("download")}</a>}
      </div>
      <Flex gap={2} className={styles.photoActions}>
        <Button variant="outlined" disabled={disabled || photo.is_main || photo.status !== "ready"}
          onClick={() => mutate(() => setDraftMainPhoto(draft.id, draft.version, photo.id))}>
          {t("setMain")}</Button>
        <Button variant="outlined" disabled={disabled} className={styles.dangerAction}
          onClick={() => onRemove(photo.id)}>{t("deletePhoto")}</Button>
      </Flex>
    </div>
  </article>
}
