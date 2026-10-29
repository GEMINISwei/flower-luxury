"use client"
import { useEffect, useMemo, useState } from "react"
import { unstable_rethrow } from "next/navigation"
import { Button, FormDialog, SelectInput, useActionSubmit } from "@/shared/ui"
import { useLocale } from "@/shared/i18n/context"
import { translate } from "@/shared/i18n/dictionary"
import { draftMessages } from "../i18n"
import { loadMoveTargets, moveMessage } from "../actions"
import { moveTargets } from "../capabilities"
import type { DraftSummary, MessageInfo } from "../types"

export default function MoveMessageDialog({ message, version, onClose, onMoved }: {
  message: MessageInfo; version: number | null; onClose: () => void; onMoved: () => void
}) {
  const locale = useLocale()
  const t = useMemo(() => translate(draftMessages, locale), [locale])
  const [targets, setTargets] = useState<DraftSummary[]>([])
  const [target, setTarget] = useState("")
  const [cursor, setCursor] = useState<string | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const { isPending, submit } = useActionSubmit()
  useEffect(() => {
    let active = true
    loadMoveTargets(message.source_key).then((result) => {
      if (!active) return
      setTargets(result.items); setCursor(result.meta.nextCursor)
      setError(result.errorMessage); setLoading(false)
    }).catch((error) => { unstable_rethrow(error); if (active) { setError(t("failed")); setLoading(false) } })
    return () => { active = false }
  }, [message.source_key, t])
  async function more(reset = false) {
    setLoading(true)
    try {
      const nextCursor = reset ? undefined : cursor ?? undefined
      const result = await loadMoveTargets(message.source_key, nextCursor)
      if (!result.errorMessage) {
        setTargets((current) => reset ? result.items : [...current, ...result.items])
        setCursor(result.meta.nextCursor)
      }
      setError(result.errorMessage)
    } catch (error) { unstable_rethrow(error); setError(t("failed")) }
    finally { setLoading(false) }
  }
  function move() {
    const selected = targets.find((item) => item.id === target)
    if (!selected) { setError(t("choose")); return }
    submit(() => moveMessage(message.id, selected.id, selected.version, version), {
      onError: setError, onSuccess: onMoved,
    })
  }
  const available = moveTargets(targets, message.source_key, message.draft_id)
  return <FormDialog title={t("moveMessage")} open isPending={isPending || loading}
    submitText={t("move")} onClose={onClose}
    onSubmit={(event) => { event.preventDefault(); move() }}>
    <p>{t("moveHint")}</p>
    <SelectInput label={t("target")} value={target} onChange={setTarget} disabled={isPending || loading}
      options={[{ value: "", label: t("choose") }, ...available.map((item) => ({
        value: item.id, label: `${item.fields.name || t("unnamed")} (${item.id.slice(0, 8)})`,
      }))]} />
    {!loading && !available.length && <p>{t("noTargets")}</p>}
    {cursor && <Button variant="outlined" disabled={loading || isPending}
      onClick={() => void more()}>{t("loadMore")}</Button>}
    {error && <Button variant="outlined" disabled={loading || isPending}
      onClick={() => void more(true)}>{t("retry")}</Button>}
    {error && <p role="alert">{error}</p>}
  </FormDialog>
}
