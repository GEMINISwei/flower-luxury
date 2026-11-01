"use client"
import { useState } from "react"
import { ConfirmDialog } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ApiResponse } from "@/shared/api/contract"
import { deleteDraftPhoto } from "../actions"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"
import DraftGallery from "./DraftGallery"
import DraftUpload from "./DraftUpload"
import styles from "./drafts.module.css"

type Mutation = (run: () => Promise<ApiResponse<DraftInfo>>) => void
export default function DraftPhotos({ draft, disabled, mutate, onError }: {
  draft: DraftInfo; disabled: boolean; mutate: Mutation; onError: (message: string) => void
}) {
  const t = useT(draftMessages)
  const [removing, setRemoving] = useState<string | null>(null)
  return <section className={styles.panel} aria-label={t("photos")}>
    <div className={styles.sectionHeader}><h2>{t("photos")}</h2>
      <span className={styles.count}>{draft.photos.length}</span>
      <DraftUpload draft={draft} disabled={disabled} mutate={mutate} onError={onError} /></div>
    <DraftGallery draft={draft} disabled={disabled} mutate={mutate} onRemove={setRemoving} />
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
