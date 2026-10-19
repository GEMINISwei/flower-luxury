"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, Container, ErrorState, PageHeader, Surface, TextInput, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { Schema } from "@/shared/api/contract"
import { exchangeMessages } from "../i18n"
import { validateRate } from "../validation"
import { updateExchangeRate } from "../actions"
import styles from "./exchange.module.css"

export default function ExchangeSettings({ settings, errorMessage }: {
  settings: Schema<"ExchangeRateSettings"> | null; errorMessage: string
}) {
  const t = useT(exchangeMessages)
  const locale = useLocale()
  const router = useRouter()
  const [rate, setRate] = useState(settings?.rate ?? "")
  const [error, setError] = useState<string>()
  const [message, setMessage] = useState("")
  const [failure, setFailure] = useState("")
  const { isPending, submit, fieldError } = useActionSubmit()
  function save() {
    const invalid = validateRate(rate, locale)
    setError(invalid); setMessage(""); setFailure("")
    if (invalid) return
    submit(() => updateExchangeRate(rate), {
      onSuccess: () => { setMessage(t("saved")); router.refresh() }, onError: setFailure,
    })
  }
  return <Container size="lg" padded><PageHeader title={t("title")} subtitle={t("subtitle")} />
    {errorMessage ? <ErrorState>{errorMessage}</ErrorState> : <Surface>
      <form
        className={styles.form} onSubmit={(event) => { event.preventDefault(); save() }} noValidate>
        <p>{settings?.rate ? t("current", { rate: settings.rate }) : t("unconfigured")}</p>
        <TextInput label={t("label")} value={rate} required disabled={isPending}
          onChange={(value) => { setRate(value); setError(undefined); setMessage("") }}
          error={error ?? fieldError("rate")} />
        <p className={styles.hint}>{t("hint")}</p>
        {settings?.updated_at && <p className={styles.hint}>{t("updated", {
          name: settings.operator_name ?? "—",
          time: new Date(settings.updated_at).toLocaleString(
            locale === "zh" ? "zh-TW" : "en-US", { timeZone: "Asia/Taipei" },
          ),
        })}</p>}
        {failure && <p role="alert">{failure}</p>}{message && <p role="status">{message}</p>}
        <div>
      <Button type="submit" disabled={isPending}>{t(isPending ? "saving" : "save")}</Button></div>
      </form>
    </Surface>}
  </Container>
}
