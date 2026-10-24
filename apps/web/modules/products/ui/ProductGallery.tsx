"use client"

import Image from "next/image"
import { ImageOff, Check, Trash2, Download } from "lucide-react"
import { Button, ICON_SIZE, StatusBadge } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { PhotoInfo, ProductStatus } from "../types"
import { gallerySelection, photoCapabilities } from "../capabilities"
import { productMessages } from "../i18n"
import styles from "./product-detail.module.css"

export default function ProductGallery({ photos, name, status, isPending, onSetMain, onDelete }: {
  photos: PhotoInfo[]; name: string; status: ProductStatus; isPending: boolean;
  onSetMain: (id: string) => void; onDelete: (id: string) => void
}) {
  const t = useT(productMessages)
  const gallery = gallerySelection(photos, null)
  return <section className={styles.imagePanel} aria-label={t("photos")}>
    {!gallery.selected && <div className={styles.placeholder}>
      <ImageOff size={ICON_SIZE.lg} aria-hidden /><span>{t("noPhotos")}</span>
    </div>}
    {gallery.photos.map((photo, index) => {
      const isMain = photo.id === gallery.selected?.id
      const caps = photoCapabilities(status, isMain)
      return <figure key={photo.id} className={styles.imageCard} data-main={isMain}>
        <a className={styles.imageFrame} href={photo.url} target="_blank" rel="noreferrer">
          <Image unoptimized width={800} height={800} src={photo.url}
            alt={`${name} · ${t("photoPreview")} ${index + 1}`} className={styles.mainImage} />
          {isMain && <span className={styles.mainBadge}>
            <StatusBadge label={t("main")} variant="warning" /></span>}
        </a>
        <figcaption className={styles.photoActions}>
          {photo.download_url ? <a className={styles.downloadPhoto} href={photo.download_url}
            download><Download size={ICON_SIZE.sm} aria-hidden />{t("downloadOriginal")}</a>
            : <span className={styles.originalUnavailable}>{t("originalUnavailable")}</span>}
          {caps.canSetMain && <Button variant="outlined" disabled={isPending}
            icon={<Check size={ICON_SIZE.sm} aria-hidden />}
            onClick={() => onSetMain(photo.id)}>
            {t("setMain")}</Button>}
          {caps.canDelete && <Button variant="outlined" disabled={isPending}
            className={styles.deletePhotoButton} icon={<Trash2 size={ICON_SIZE.sm} aria-hidden />}
            onClick={() => onDelete(photo.id)}>{t("delete")}</Button>}
        </figcaption>
      </figure>
    })}
  </section>
}
