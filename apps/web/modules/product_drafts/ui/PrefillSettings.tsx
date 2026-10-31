"use client"
import { useId, useRef, useState } from "react"
import { Trash2 } from "lucide-react"
import { Button, Container, ErrorState, PageHeader, TextInput, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { previewPrefill, savePrefillSettings } from "../actions"
import { parsePrefillConditions, prefillConditionState } from "../capabilities"
import { prefillMessages } from "../i18n"
import type { PrefillSettingsInfo } from "../types"
import styles from "./drafts.module.css"

function usePrefillForm(initial: PrefillSettingsInfo | null) {
  const t = useT(prefillMessages)
  const [settings, setSettings] = useState(initial)
  const [conditions, setConditions] = useState(() =>
    parsePrefillConditions(initial?.supplement ?? "").map((text, index) => ({ id: String(index), text })))
  const nextConditionId = useRef(conditions.length)
  const [text, setText] = useState("")
  const [result, setResult] = useState("")
  const [error, setError] = useState("")
  const [status, setStatus] = useState("")
  const { submit, isPending } = useActionSubmit()
  const controls = prefillConditionState(conditions.map((condition) => condition.text),
    settings?.configured ?? false)
  function addCondition() {
    const id = String(nextConditionId.current++)
    setConditions((current) => [...current, { id, text: "" }])
  }
  function save() {
    setError(""); setStatus("")
    if (!controls.canSave) { setError(t("conditionsTooLong")); return }
    submit(async () => {
      const response = await savePrefillSettings(controls.supplement, settings?.revision ?? 0)
      if (response.status === "success") setSettings(response.data)
      return response
    }, { onSuccess: () => setStatus(t("saved")), onError: setError })
  }
  function preview() {
    setError(""); setStatus(""); setResult("")
    if (!controls.canPreview) return
    if (!text.trim()) { setError(t("required")); return }
    submit(async () => {
      const response = await previewPrefill(text, controls.supplement)
      if (response.status === "success") setResult(JSON.stringify(response.data, null, 2))
      return response
    }, { onSuccess: () => {}, onError: setError })
  }
  return { settings, conditions, setConditions, addCondition, controls, text, setText,
    result, error, status,
    save, preview, isPending }
}

type PrefillForm = ReturnType<typeof usePrefillForm>

function ConditionList({ form }: { form: PrefillForm }) {
  const t = useT(prefillMessages)
  return <div className={styles.stack}>
    <div className={styles.sectionHeader}><h3>{t("supplement")}</h3>
      <Button variant="outlined" disabled={form.isPending} onClick={form.addCondition}>
        {t("addCondition")}</Button></div>
    <ol className={styles.conditions}>
      {form.conditions.map((condition, index) =>
        <li key={condition.id} className={styles.condition}>
          <span className={styles.conditionNumber} aria-hidden="true">{index + 1}.</span>
          <TextInput ariaLabel={t("condition", { number: index + 1 })} value={condition.text}
            disabled={form.isPending} onChange={(text) => form.setConditions(form.conditions.map(
              (item) => item.id === condition.id ? { ...item, text } : item))} />
          <button type="button" className={styles.removeCondition} disabled={form.isPending}
            aria-label={t("deleteCondition", { number: index + 1 })} onClick={() =>
              form.setConditions(form.conditions.filter((item) => item.id !== condition.id))}>
            <Trash2 className={styles.icon} aria-hidden="true" /></button>
        </li>)}
    </ol>
    {form.controls.tooLong && <p role="alert">{t("conditionsTooLong")}</p>}
  </div>
}

function PrefillTest({ form }: { form: PrefillForm }) {
  const t = useT(prefillMessages)
  const textId = useId()
  return <div className={styles.stack}>
    <h3>{t("test")}</h3>
    <div className={styles.notes}><label htmlFor={textId}>{t("testText")}</label>
      <textarea id={textId} value={form.text} maxLength={200000} disabled={form.isPending}
        onChange={(event) => form.setText(event.target.value)} /></div>
    <p className={styles.hint}>{t("testHint")}</p>
    <div><Button variant="outlined" disabled={form.isPending || !form.controls.canPreview}
      onClick={form.preview}>{t("test")}</Button></div>
    {form.result && <pre aria-label={t("result")} className={styles.json}>{form.result}</pre>}
  </div>
}

export default function PrefillSettings({ initial, errorMessage }: {
  initial: PrefillSettingsInfo | null; errorMessage: string
}) {
  const t = useT(prefillMessages)
  const form = usePrefillForm(initial)
  const formId = useId()
  return <Container size="lg" padded>
    <PageHeader title={t("title")} actions={<Button type="submit" form={formId}
      disabled={form.isPending || !form.controls.canSave || !!errorMessage}>{t("save")}</Button>} />
    {errorMessage ? <ErrorState>{errorMessage}</ErrorState> : <div className={styles.stack}>
      <section className={styles.panel} aria-label={t("prefill")}>
        <h2>{t("prefill")}</h2>
        {!form.settings?.configured && <p className={styles.hint}>{t("unconfigured")}</p>}
        <form id={formId} className={styles.feedback}
          onSubmit={(event) => { event.preventDefault(); form.save() }}>
          <ConditionList form={form} />
        </form>
        <hr className={styles.divider} />
        <PrefillTest form={form} />
      </section>
      <div className={styles.feedback}>{form.error && <p role="alert">{form.error}</p>}
        {form.status && <p role="status">{form.status}</p>}</div>
    </div>}
  </Container>
}
