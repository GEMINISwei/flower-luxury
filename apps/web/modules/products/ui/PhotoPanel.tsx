"use client"

import { useRef, useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { Button, ConfirmDialog, StatusBadge, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { PhotoInfo } from "../types"
import { productMessages } from "../i18n"
import { validatePhotoBatch } from "../validation"
import { deletePhoto, setMainPhoto, uploadPhotos } from "../actions"
import styles from "./catalog.module.css"

export default function PhotoPanel({ id, photos, canEdit }: {
  id: string; photos: PhotoInfo[]; canEdit: boolean
}) {
  const t = useT(productMessages)
  const locale = useLocale()
  const router = useRouter()
  const input = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState("")
  const [removing, setRemoving] = useState<string | null>(null)
  const { isPending, submit } = useActionSubmit()
  function done() { setRemoving(null); setError(""); router.refresh() }
  function upload() {
    const validation = validatePhotoBatch(files, locale)
    if (validation) { setError(validation); return }
    const body = new FormData()
    files.forEach((file) => body.append("files", file))
    submit(() => uploadPhotos(id, body), { onError: setError, onSuccess: () => {
      setFiles([]); if (input.current) input.current.value = ""; done()
    } })
  }
  function remove() {
    if (!removing) return
    submit(() => deletePhoto(id, removing), { onSuccess: done, onError: setError })
  }
  return <div className={styles.stack}>
    <h2>{t("photos")}</h2>
    {!removing && error && <p className={styles.error} role="alert">{error}</p>}
    {!photos.length && <p className={styles.muted}>{t("noPhotos")}</p>}
    <div className={styles.gallery}>{photos.map((photo) =>
      <div key={photo.id} className={styles.photo}>
      <a href={photo.url} target="_blank" rel="noreferrer">
        <Image unoptimized width={512} height={512} src={photo.url} alt={t("photos")} />
      </a>
      {photo.is_main && <StatusBadge label={t("main")} variant="success" />}
      {canEdit && <div className={styles.actions}>
        {!photo.is_main && <Button variant="outlined" disabled={isPending} onClick={() =>
          submit(() => setMainPhoto(id, photo.id), { onSuccess: done, onError: setError })}>
          {t("setMain")}</Button>}
        <Button variant="outlined" disabled={isPending}
          onClick={() => { setError(""); setRemoving(photo.id) }}>
          {t("delete")}</Button>
      </div>}
    </div>)}</div>
    {canEdit && <div className={styles.upload}>
      <label>{t("upload")}<input ref={input} type="file" multiple
        accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
        disabled={isPending} onChange={(event) => {
          const selected = Array.from(event.target.files ?? [])
          setFiles(selected); setError(validatePhotoBatch(selected, locale) ?? "")
        }} /></label>
      <p className={styles.muted}>{t("uploadHint")}</p>
      <div><Button disabled={isPending || !files.length || Boolean(error)} onClick={upload}>
        {isPending ? t("saving") : t("upload")}</Button></div>
    </div>}
    <ConfirmDialog title={t("delete")} open={Boolean(removing)} isPending={isPending}
      confirmText={t("delete")} onClose={() => setRemoving(null)} onConfirm={remove}>
      <p>{t("deletePhotoConfirm")}</p>
      {error && <p className={styles.error} role="alert">{error}</p>}
    </ConfirmDialog>
  </div>
}
