"use client"
import { useRef } from "react"
import { Upload } from "lucide-react"
import { Button, ICON_SIZE } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import { validatePhotoBatch } from "@/modules/products/public.client"
import type { ApiResponse } from "@/shared/api/contract"
import { uploadDraftPhotos } from "../actions"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"

export default function DraftUpload({ draft, disabled, mutate, onError }: {
  draft: DraftInfo; disabled: boolean; onError: (message: string) => void;
  mutate: (run: () => Promise<ApiResponse<DraftInfo>>) => void
}) {
  const t = useT(draftMessages)
  const locale = useLocale()
  const input = useRef<HTMLInputElement>(null)
  function select(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ""
    if (!files.length) return
    const error = validatePhotoBatch(files, locale)
    if (error) { onError(error); return }
    const data = new FormData()
    files.forEach((file) => data.append("files", file))
    mutate(() => uploadDraftPhotos(draft.id, draft.version, data))
  }
  return <>
    <Button variant="outlined" disabled={disabled} icon={<Upload size={ICON_SIZE.sm} />}
      onClick={() => input.current?.click()}>{t("uploadPhotos")}</Button>
    <input ref={input} type="file" multiple hidden aria-label={t("uploadPhotos")}
      accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
      disabled={disabled} onChange={select} />
  </>
}
