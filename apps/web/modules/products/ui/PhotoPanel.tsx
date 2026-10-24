"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { ConfirmDialog, Modal, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { PhotoInfo, ProductStatus } from "../types"
import { productMessages } from "../i18n"
import { validatePhotoBatch } from "../validation"
import { productCapabilities } from "../capabilities"
import { deletePhoto, setMainPhoto, uploadPhotos } from "../actions"
import ProductGallery from "./ProductGallery"
import PhotoPicker from "./PhotoPicker"
import styles from "./product-detail.module.css"

export default function PhotoPanel({ id, name, photos, status, onClose }: {
  id: string; name: string; photos: PhotoInfo[]; status: ProductStatus; onClose: () => void
}) {
  const t = useT(productMessages)
  const locale = useLocale()
  const router = useRouter()
  const [error, setError] = useState("")
  const [removing, setRemoving] = useState<string | null>(null)
  const { isPending, submit } = useActionSubmit()
  const { canEdit } = productCapabilities(status)
  function done() { setRemoving(null); setError(""); router.refresh() }
  function upload(files: File[]) {
    if (!files.length) return
    const validation = validatePhotoBatch(files, locale)
    if (validation) { setError(validation); return }
    const body = new FormData()
    files.forEach((file) => body.append("files", file))
    setError("")
    submit(() => uploadPhotos(id, body), { onError: setError, onSuccess: done })
  }
  function remove() {
    if (!removing) return
    submit(() => deletePhoto(id, removing), { onSuccess: done, onError: setError })
  }
  function close(open: boolean) {
    if (open) return
    if (removing) { setRemoving(null); return }
    onClose()
  }
  return <>
    <Modal title={t("photos")} open onOpenChange={close}
      headerActions={canEdit && <PhotoPicker compact disabled={isPending} onSelect={upload} />}>
      <div className={styles.stack}>
        {!removing && error && <p className={styles.photoError} role="alert">{error}</p>}
        <ProductGallery photos={photos} name={name} status={status} isPending={isPending}
          onSetMain={(photoId) => submit(() => setMainPhoto(id, photoId),
            { onSuccess: done, onError: setError })}
          onDelete={(photoId) => { setError(""); setRemoving(photoId) }} />
      </div>
    </Modal>
    <ConfirmDialog title={t("delete")} open={Boolean(removing)} isPending={isPending}
      confirmText={t("delete")} onClose={() => setRemoving(null)} onConfirm={remove}>
      <p>{t("deletePhotoConfirm")}</p>
      {error && <p className={styles.photoError} role="alert">{error}</p>}
    </ConfirmDialog>
  </>
}
