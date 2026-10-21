"use client"

import { useState } from "react"
import Image from "next/image"
import { ImageOff } from "lucide-react"
import { ICON_SIZE } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { PhotoInfo } from "../types"
import { gallerySelection } from "../capabilities"
import { productMessages } from "../i18n"
import styles from "./product-detail.module.css"

export default function ProductGallery({ photos, name }: { photos: PhotoInfo[]; name: string }) {
  const t = useT(productMessages)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const gallery = gallerySelection(photos, selectedId)
  return <section className={styles.imagePanel} aria-label={t("photos")}>
    {gallery.selected ? <a className={styles.imageFrame} href={gallery.selected.url}
      target="_blank" rel="noreferrer">
      <Image unoptimized width={800} height={800} src={gallery.selected.url}
        alt={name} className={styles.mainImage} loading="eager" />
    </a> : <div className={styles.placeholder}>
      <ImageOff size={ICON_SIZE.lg} aria-hidden /><span>{t("noPhotos")}</span>
    </div>}
    <div className={styles.thumbnails}>{gallery.photos.map((photo, index) =>
      <button type="button" key={photo.id} className={styles.thumbnail}
        aria-label={`${t("photoPreview")} ${index + 1}`} aria-pressed={photo.id === gallery.selected?.id}
        onClick={() => setSelectedId(photo.id)}>
        <Image unoptimized width={160} height={160} src={photo.url} alt="" />
      </button>)}</div>
  </section>
}
