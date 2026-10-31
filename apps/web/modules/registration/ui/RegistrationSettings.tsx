"use client"

import { useState } from "react"
import { Save } from "lucide-react"
import { ICON_SIZE, ErrorState, FormPageShell, Surface, TextInput, useActionSubmit } from "@/shared/ui"
import { USERS_PATH } from "@/modules/users/manifest"
import { createActionFormData } from "@/shared/api/action-form-data"
import { useLocale, useT } from "@/shared/i18n/context"
import { updateRegistrationKey } from "../actions"
import { registrationMessages } from "../i18n"
import { validateRegistrationKey } from "../validation"
import styles from "./registration.module.css"

export default function RegistrationSettings({ configured, errorMessage }: {
  configured: boolean
  errorMessage: string
}) {
  const t = useT(registrationMessages)
  const locale = useLocale()
  const [key, setKey] = useState("")
  const [error, setError] = useState<string>()
  const [message, setMessage] = useState("")
  const [failure, setFailure] = useState("")
  const { isPending, submit, fieldError } = useActionSubmit()

  function handleSubmit() {
    const validationError = validateRegistrationKey(key, locale)
    setError(validationError)
    setMessage("")
    setFailure("")
    if (validationError) return
    submit(() => updateRegistrationKey(createActionFormData({ registration_key: key })), {
      onSuccess: () => { setKey(""); setMessage(t("saved")) },
      onError: setFailure, errorFallback: t("saveFailed"),
    })
  }

  return (
    <FormPageShell title={t("settingsTitle")} subtitle={t("settingsDescription")}
      backHref={USERS_PATH} backLabel={t("backToUsers")}
      actions={[{ label: t("save"), icon: <Save size={ICON_SIZE.md} />, primary: true,
        type: "submit", form: "registration-settings", disabled: isPending || Boolean(errorMessage) }]}>
      <Surface>
        <form id="registration-settings" action={handleSubmit} className={styles.form} noValidate>
          {errorMessage ? <ErrorState>{errorMessage}</ErrorState> : <>
            <p>{t(configured ? "configured" : "unconfigured")}</p>
            <p className={styles.description}>{t("changeDescription")}</p>
            <TextInput label={t("newKey")} type="password" autoComplete="new-password"
              value={key} required disabled={isPending} error={error ?? fieldError("registration_key")}
              onChange={(value) => { setKey(value); setError(undefined); setMessage("") }} />
          </>}
          {failure && <p role="alert">{failure}</p>}
          {message && <p role="status">{message}</p>}
        </form>
      </Surface>
    </FormPageShell>
  )
}
