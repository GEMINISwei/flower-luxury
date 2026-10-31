"use client"
import { useId, useState } from "react"
import { Button, Container, ErrorState, PageHeader, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { previewPrefill, savePrefillSettings } from "../actions"
import { prefillMessages } from "../i18n"
import type { PrefillSettingsInfo } from "../types"
import styles from "./drafts.module.css"

function usePrefillForm(initial: PrefillSettingsInfo | null) {
  const t = useT(prefillMessages)
  const [settings, setSettings] = useState(initial)
  const [supplement, setSupplement] = useState(initial?.supplement ?? "")
  const [text, setText] = useState("")
  const [result, setResult] = useState("")
  const [error, setError] = useState("")
  const [status, setStatus] = useState("")
  const { submit, isPending } = useActionSubmit()
  function save() {
    setError(""); setStatus("")
    submit(async () => {
      const response = await savePrefillSettings(supplement, settings?.revision ?? 0)
      if (response.status === "success") setSettings(response.data)
      return response
    }, { onSuccess: () => setStatus(t("saved")), onError: setError })
  }
  function preview() {
    setError(""); setStatus(""); setResult("")
    if (!text.trim()) { setError(t("required")); return }
    submit(async () => {
      const response = await previewPrefill(text, supplement)
      if (response.status === "success") setResult(JSON.stringify(response.data, null, 2))
      return response
    }, { onSuccess: () => {}, onError: setError })
  }
  return { settings, supplement, setSupplement, text, setText, result, error, status,
    save, preview, isPending }
}

export default function PrefillSettings({ initial, errorMessage }: {
  initial: PrefillSettingsInfo | null; errorMessage: string
}) {
  const t = useT(prefillMessages)
  const form = usePrefillForm(initial)
  const baseId = useId()
  const supplementId = useId()
  const textId = useId()
  return <Container size="lg" padded><PageHeader title={t("title")} subtitle={t("subtitle")} />
    {errorMessage ? <ErrorState>{errorMessage}</ErrorState> : <div className={styles.stack}>
      <div className={styles.panel}>
        <p className={styles.hint}>
          {t(form.settings?.configured ? "configured" : "unconfigured")}</p>
        <div className={styles.notes}><label htmlFor={baseId}>{t("base")}</label>
          <textarea id={baseId} className={styles.prompt}
            value={form.settings?.base_prompt ?? ""} readOnly /></div>
        <form className={styles.stack}
          onSubmit={(event) => { event.preventDefault(); form.save() }}>
          <div className={styles.notes}><label htmlFor={supplementId}>{t("supplement")}</label>
            <textarea id={supplementId} value={form.supplement} maxLength={10000}
              disabled={form.isPending}
              onChange={(event) => form.setSupplement(event.target.value)} /></div>
          <p className={styles.hint}>{t("hint")}</p>
          <div><Button type="submit" disabled={form.isPending}>{t("save")}</Button></div>
        </form>
      </div>
      <section className={styles.panel} aria-label={t("result")}>
        <div className={styles.notes}><label htmlFor={textId}>{t("testText")}</label>
          <textarea id={textId} value={form.text} maxLength={200000} disabled={form.isPending}
            onChange={(event) => form.setText(event.target.value)} /></div>
        <p className={styles.hint}>{t("testHint")}</p><p className={styles.hint}>{t("limits")}</p>
        <div><Button variant="outlined" disabled={form.isPending || !form.settings?.configured}
          onClick={form.preview}>{t("test")}</Button></div>
        {form.result && <pre className={styles.json}>{form.result}</pre>}
      </section>
      <div className={styles.feedback}>{form.error && <p role="alert">{form.error}</p>}
        {form.status && <p role="status">{form.status}</p>}</div>
    </div>}
  </Container>
}
