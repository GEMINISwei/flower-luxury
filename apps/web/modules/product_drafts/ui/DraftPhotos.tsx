"use client"
import { useState } from "react"
import Image from "next/image"
import { Button, ConfirmDialog, Flex } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import { validatePhotoBatch } from "@/modules/products/public.client"
import type { ApiResponse } from "@/shared/api/contract"
import { deleteDraftPhoto, reorderDraftPhotos, setDraftMainPhoto, uploadDraftPhotos } from "../actions"
import { photoOrder } from "../capabilities"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"
import styles from "./drafts.module.css"

type Mutation = (run: () => Promise<ApiResponse<DraftInfo>>) => void
export default function DraftPhotos({ draft, disabled, mutate, onError }: {
  draft: DraftInfo; disabled: boolean; mutate: Mutation; onError: (error: string) => void
}) {
  const t = useT(draftMessages)
  const locale = useLocale()
  const [removing, setRemoving] = useState<string | null>(null)
  function upload(files: File[]) {
    if (!files.length) return
    const error = validatePhotoBatch(files, locale)
    if (error) { onError(error); return }
    const data = new FormData()
    files.forEach((file) => data.append("files", file))
    mutate(() => uploadDraftPhotos(draft.id, draft.version, data))
  }
  return <section className={styles.panel} aria-label={t("photos")}>
    <h2>{t("photos")}</h2><p className={styles.hint}>{t("uploadHint")}</p>
    <label className={styles.upload}>{t("upload")}
      <input type="file" multiple aria-label={t("upload")} disabled={disabled}
        accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
        onChange={(event) => {
          upload(Array.from(event.target.files ?? [])); event.target.value = ""
        }} />
    </label>
    {!draft.photos.length && <p>{t("noPhotos")}</p>}
    <div className={styles.photoGrid}>
      {draft.photos.map((photo, index) => <article key={photo.id} data-testid="draft-photo"
        className={styles.photo} data-main={photo.is_main}>
        {photo.url && <a href={photo.url} target="_blank" rel="noreferrer" aria-label={t("preview")}>
          <Image unoptimized src={photo.url} width={480} height={480}
            alt={t("preview")} className={styles.thumbnail} /></a>}
        <p>{t(photo.status === "failed" ? "failedPhoto" : photo.status)}
          {photo.is_main && ` · ${t("main")}`}</p>
        {photo.download_url && <a href={photo.download_url}>{t("download")}</a>}
        <Flex gap={2} className={styles.photoActions}>
          <Button variant="outlined" disabled={disabled || photo.is_main || photo.status !== "ready"}
            onClick={() => mutate(() => setDraftMainPhoto(draft.id, draft.version, photo.id))}>
            {t("setMain")}</Button>
          <Button variant="outlined" disabled={disabled || index === 0}
            onClick={() => mutate(() => reorderDraftPhotos(draft.id, draft.version,
              photoOrder(draft.photos, photo.id, -1)))}>{t("previous")}</Button>
          <Button variant="outlined" disabled={disabled || index === draft.photos.length - 1}
            onClick={() => mutate(() => reorderDraftPhotos(draft.id, draft.version,
              photoOrder(draft.photos, photo.id, 1)))}>{t("next")}</Button>
          <Button variant="outlined" disabled={disabled}
            onClick={() => setRemoving(photo.id)}>{t("deletePhoto")}</Button>
        </Flex>
      </article>)}
    </div>
    <ConfirmDialog title={t("deletePhoto")} open={Boolean(removing)} isPending={disabled}
      confirmText={t("delete")} onClose={() => setRemoving(null)} onConfirm={() => {
        if (removing) {
          const id = removing
          mutate(async () => {
            const result = await deleteDraftPhoto(draft.id, draft.version, id)
            if (result.status === "success") setRemoving(null)
            return result
          })
        }
      }}><p>{t("deletePhotoHint")}</p></ConfirmDialog>
  </section>
}
