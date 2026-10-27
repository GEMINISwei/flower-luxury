"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { productMessages } from "../i18n"
import PhotoPicker from "./PhotoPicker"
import styles from "./photo-picker.module.css"

export default function NewProductPhotos({ files, disabled, error, onSelect, onRemove }: {
  files: File[]; disabled: boolean; error: string
  onSelect: (files: File[]) => void; onRemove: (index: number) => void
}) {
  const t = useT(productMessages)
  return <section className={styles.section}>
    <h3>{t("photos")}</h3>
    <PhotoPicker disabled={disabled} onSelect={onSelect} />
    <p className={styles.hint}>{t("newPhotosHint")}</p>
    {error && <p className={styles.error} role="alert">{error}</p>}
    <div className={styles.previews}>
      {files.map((file, index) => <figure className={styles.photo} key={index}>
        <PhotoPreview file={file} />
        <figcaption>{file.name}</figcaption>
        <Button variant="outlined" disabled={disabled} onClick={() => onRemove(index)}>
          {t("removePhoto")}</Button>
      </figure>)}
    </div>
  </section>
}

function PhotoPreview({ file }: { file: File }) {
  const t = useT(productMessages)
  const image = useRef<HTMLImageElement>(null)
  const [failedFile, setFailedFile] = useState<File | null>(null)
  useEffect(() => {
    const url = URL.createObjectURL(file)
    if (image.current) image.current.src = url
    return () => URL.revokeObjectURL(url)
  }, [file])
  if (failedFile === file) {
    return <div className={styles.previewFallback}>{t("previewUnavailable")}</div>
  }
  // 暫存原檔由瀏覽器預覽, 尚未存在可供 Next Image 讀取的伺服器網址.
  // eslint-disable-next-line @next/next/no-img-element
  return <img ref={image} className={styles.preview} alt={file.name}
    onError={() => setFailedFile(file)} />
}
