"use client"
import { useEffect, useRef, useState, type ComponentProps } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { photoSelection } from "../capabilities"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"
import DraftPhoto from "./DraftPhoto"
import styles from "./drafts.module.css"

type PhotoProps = ComponentProps<typeof DraftPhoto>
export default function DraftGallery({ draft, disabled, mutate, onRemove }: {
  draft: DraftInfo; disabled: boolean; mutate: PhotoProps["mutate"];
  onRemove: (id: string) => void
}) {
  const t = useT(draftMessages)
  const [selected, setSelected] = useState<string | null>(null)
  const { id, index } = photoSelection(draft.photos, selected)
  const track = useRef<HTMLDivElement>(null)
  useEffect(() => {
    // 以照片 ID 保留選取, 刪除或補圖後再對齊目前的位置.
    track.current?.scrollTo({ left: Math.max(0, index) * track.current.clientWidth })
  }, [id, index, draft.photos.length])
  function select(position: number) {
    const photo = draft.photos[position]
    if (photo) setSelected(photo.id)
  }
  if (!draft.photos.length) return <div className={styles.emptyPhoto}>{t("noPhotos")}</div>
  return <div className={styles.gallery}>
    <div className={styles.galleryTrack} ref={track} role="region" aria-label={t("photoBrowser")}
      tabIndex={0} onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return
        if (event.key === "ArrowLeft") { event.preventDefault(); select(index - 1) }
        if (event.key === "ArrowRight") { event.preventDefault(); select(index + 1) }
      }} onScroll={() => {
        const element = track.current
        if (element?.clientWidth) select(Math.round(element.scrollLeft / element.clientWidth))
      }}>
      {draft.photos.map((photo) => <DraftPhoto key={photo.id} photo={photo}
        draft={draft} disabled={disabled} mutate={mutate} onRemove={onRemove} />)}
    </div>
    <div className={styles.galleryNav}>
      <Button variant="outlined" disabled={index <= 0} onClick={() => select(index - 1)}
        icon={<ChevronLeft className={styles.icon} aria-hidden="true" />}>
        {t("previousPhoto")}</Button>
      <p className={styles.photoCounter} aria-live="polite" aria-atomic="true">
        {t("photoCounter", { current: index + 1, total: draft.photos.length })}</p>
      <Button variant="outlined" disabled={index >= draft.photos.length - 1}
        onClick={() => select(index + 1)}>
        {t("nextPhoto")}<ChevronRight className={styles.icon} aria-hidden="true" /></Button>
    </div>
  </div>
}
