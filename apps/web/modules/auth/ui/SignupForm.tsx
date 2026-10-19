"use client"

import Link from "next/link"
import { useState } from "react"
import { Button, TextInput, useActionSubmit } from "@/shared/ui"
import { createActionFormData } from "@/shared/api/action-form-data"
import { useLocale, useT } from "@/shared/i18n/context"
import { LOGIN_PATH } from "@/shared/session/login-contract"
import { signup } from "../actions"
import {
  registrationMessages, validateSignup, type SignupErrors, type SignupValues,
} from "@/modules/registration/public.client"
import styles from "./auth.module.css"

const EMPTY: SignupValues = {
  username: "", nickname: "", password: "", confirm_password: "", registration_key: "",
}

export default function SignupForm() {
  const t = useT(registrationMessages)
  const locale = useLocale()
  const [values, setValues] = useState(EMPTY)
  const [errors, setErrors] = useState<SignupErrors>({})
  const [message, setMessage] = useState("")
  const [created, setCreated] = useState(false)
  const { isPending, submit, fieldError } = useActionSubmit()

  function handleSubmit() {
    const nextErrors = validateSignup(values, locale)
    setErrors(nextErrors)
    setMessage("")
    if (Object.values(nextErrors).some(Boolean)) return
    submit(() => signup(createActionFormData(values)), {
      onSuccess: () => { setValues(EMPTY); setCreated(true) },
      onError: setMessage, errorFallback: t("signupFailed"),
    })
  }

  const fields = [
    { key: "nickname", label: "nickname", type: "text", autoComplete: "nickname" },
    { key: "username", label: "username", type: "text", autoComplete: "username" },
    { key: "password", label: "password", type: "password", autoComplete: "new-password" },
    { key: "confirm_password", label: "confirmPassword", type: "password", autoComplete: "new-password" },
    { key: "registration_key", label: "registrationKey", type: "password", autoComplete: "off" },
  ] as const

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <form action={handleSubmit} className={styles.fields} noValidate>
          <h1 className={styles.signupTitle}>{t("signupTitle")}</h1>
          <p className={styles.subtitle}>{t("signupDescription")}</p>
          {created ? <p role="status">{t("signupSuccess")}</p> : <>
            {message && <p role="alert">{message}</p>}
            {fields.map(({ key, label, ...input }) => <TextInput
              key={key} {...input} label={t(label)} name={key} value={values[key]}
              required disabled={isPending} error={errors[key] ?? fieldError(key)}
              onChange={(value) => {
                setValues((previous) => ({ ...previous, [key]: value }))
                setErrors((previous) => ({ ...previous, [key]: undefined }))
                setMessage("")
              }}
            />)}
            <Button type="submit" disabled={isPending} fullWidth>
              {isPending ? t("signingUp") : t("signup")}
            </Button>
          </>}
          <Link className={styles.signupLink} href={LOGIN_PATH}>{t("backToLogin")}</Link>
        </form>
      </section>
    </main>
  )
}
