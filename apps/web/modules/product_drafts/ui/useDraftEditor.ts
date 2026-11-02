"use client"
import { useEffect, useRef, useState, useTransition } from "react"
import { unstable_rethrow } from "next/navigation"
import type { ApiResponse } from "@/shared/api/contract"
import { getApiResponseErrorMessage } from "@/shared/api/error"
import { useT } from "@/shared/i18n/context"
import { approveDraft, reloadDraft, saveDraft } from "../actions"
import { draftPayload, draftValidation, draftValues, reloadDraftValues } from "../capabilities"
import { draftMessages } from "../i18n"
import type { DraftInfo, DraftValues } from "../types"

function useDraftRequest(onDraft: (draft: DraftInfo) => void) {
  const t = useT(draftMessages)
  const [error, setError] = useState("")
  const [status, setStatus] = useState("")
  const [stale, setStale] = useState(false)
  const [pending, startTransition] = useTransition()
  const busy = useRef(false)
  function run(operation: () => Promise<ApiResponse<DraftInfo>>, onSuccess?: () => void) {
    if (busy.current) return
    busy.current = true
    setError(""); setStatus("")
    startTransition(async () => {
      try {
        const result = await operation()
        if (result.status === "success") {
          onDraft(result.data); setStale(false); onSuccess?.()
        } else {
          setStale(result.code === 409)
          setError(getApiResponseErrorMessage(result, t("actionFailed")))
        }
      } catch (error) { unstable_rethrow(error); setError(t("actionFailed")) }
      finally { busy.current = false }
    })
  }
  return { error, status, stale, pending, setError, setStatus, run }
}

export default function useDraftEditor(initial: DraftInfo, source?: string) {
  const t = useT(draftMessages)
  const [draft, setDraft] = useState(initial)
  const [values, setValues] = useState(() => draftValues(initial.fields))
  const [saved, setSaved] = useState(() => JSON.stringify(draftValues(initial.fields)))
  const [comparison, setComparison] = useState<DraftInfo | null>(null)
  const [manual, setManual] = useState<(keyof DraftValues)[]>([])
  const request = useDraftRequest(setDraft)
  const { run, setError, setStatus } = request
  const dirty = JSON.stringify(values) !== saved
  useEffect(() => {
    if (!dirty) return
    function warn(event: BeforeUnloadEvent) { event.preventDefault() }
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [dirty])
  function validate(approving: boolean) {
    const errors = draftValidation(values, approving)
    if (errors.length) {
      setError(t("missing", { fields: errors.map((key) => t(key)).join(", ") })); return false
    }
    if (approving && (!draft.photos.length || draft.photos.some((photo) => photo.status !== "ready"))) {
      setError(t("photoNotReady")); return false
    }
    return true
  }
  function save(approving = false) {
    if (!validate(approving)) return
    run(async () => {
      const result = await saveDraft(draft.id, draft.version, draftPayload(values), manual)
      if (result.status === "success") {
        setDraft(result.data); setSaved(JSON.stringify(values)); setComparison(null); setManual([])
        if (approving) return await approveDraft(draft.id, result.data.version, source)
      } else if (approving && result.code === 404) {
        return await approveDraft(draft.id, draft.version, source)
      }
      return result
    }, () => setStatus(t("saved")))
  }
  function reload() {
    run(async () => {
      const result = await reloadDraft(draft.id)
      if (result.status === "success") {
        setComparison(result.data)
        setValues(reloadDraftValues(values, JSON.parse(saved) as DraftValues, result.data.fields))
        setSaved(JSON.stringify(draftValues(result.data.fields)))
      }
      return result
    }, () => setStatus(t("reloaded")))
  }
  function set(key: keyof DraftValues, value: string) {
    setValues((current) => ({ ...current, [key]: value })); setStatus("")
    setManual((current) => current.includes(key) ? current : [...current, key])
  }
  return { ...request, draft, values, comparison, dirty, set, save, validate, reload }
}
