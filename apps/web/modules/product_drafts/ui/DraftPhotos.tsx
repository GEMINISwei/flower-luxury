"use client"
import { useState } from "react"
import { ConfirmDialog } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import { validatePhotoBatch } from "@/modules/products/public.client"
import type { ApiResponse } from "@/shared/api/contract"
import { deleteDraftPhoto, uploadDraftPhotos } from "../actions"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"
import DraftGallery from "./DraftGallery"
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
    <div className={styles.sectionHeader}><h2>{t("photos")}</h2>
      <span className={styles.count}>{draft.photos.length}</span></div>
    <DraftGallery draft={draft} disabled={disabled} mutate={mutate} onRemove={setRemoving} />
    <div className={styles.uploadSection}><p className={styles.hint}>{t("uploadHint")}</p>
        <label className={styles.upload}>{t("upload")}
          <input type="file" multiple aria-label={t("upload")} disabled={disabled}
            accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
            onChange={(event) => {
              upload(Array.from(event.target.files ?? [])); event.target.value = ""
            }} />
        </label>
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
