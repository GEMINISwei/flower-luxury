"use client"

import Image from "next/image"
import { ImageOff } from "lucide-react"
import { ICON_SIZE, StatusBadge } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { PhotoInfo } from "../types"
import { gallerySelection } from "../capabilities"
import { productMessages } from "../i18n"
import styles from "./product-detail.module.css"

export default function ProductGallery({ photos, name }: { photos: PhotoInfo[]; name: string }) {
  const t = useT(productMessages)
  const gallery = gallerySelection(photos, null)
  return <section className={styles.imagePanel} aria-label={t("photos")}>
    {!gallery.selected && <div className={styles.placeholder}>
      <ImageOff size={ICON_SIZE.lg} aria-hidden /><span>{t("noPhotos")}</span>
    </div>}
    {gallery.photos.map((photo, index) => <figure key={photo.id} className={styles.imageCard}
      data-main={photo.id === gallery.selected?.id}>
      <figcaption className={styles.photoCaption}>
        {photo.id === gallery.selected?.id ? <StatusBadge label={t("main")} variant="warning" />
          : `${t("photoPreview")} ${index + 1}`}
      </figcaption>
      <a className={styles.imageFrame} href={photo.url} target="_blank" rel="noreferrer">
        <Image unoptimized width={800} height={800} src={photo.url}
          alt={`${name} · ${t("photoPreview")} ${index + 1}`} className={styles.mainImage} />
      </a>
    </figure>)}
  </section>
}
