"use client"

import { type FormEvent, useState } from "react"
import { FormDialog, TextInput, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import { validateNewPassword } from "@/modules/auth/public.client"
import { createActionFormData } from "@/shared/api/action-form-data"
import { usersMessages } from "../i18n"
import { createUser } from "../actions"

type CreateUserDialogProps = {
  open: boolean
  onClose: () => void
  onSuccess: (message: string) => void
  onError: (message: string) => void
}

export default function CreateUserDialog({
  open,
  onClose,
  onSuccess,
  onError,
}: CreateUserDialogProps) {
  const t = useT(usersMessages)
  const locale = useLocale()
  const [username, setUsername] = useState("")
  const [nickname, setNickname] = useState("")
  const [password, setPassword] = useState("")
  const { isPending, submit, fieldError, clearFieldErrors } = useActionSubmit()

  function resetState() {
    setUsername("")
    setNickname("")
    setPassword("")
    clearFieldErrors()
  }

  function handleClose() {
    resetState()
    onClose()
  }

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const passwordError = validateNewPassword(password, locale)
    if (!username.trim() || !nickname.trim() || passwordError) {
      onError(passwordError ?? t("usernameNicknameRequired"))
      return
    }

    submit(
      () => createUser(createActionFormData({
        username: username.trim(),
        nickname: nickname.trim(),
        password,
      })),
      {
        onSuccess: () => {
          resetState()
          onSuccess(t("userCreated"))
        },
        onError,
        errorFallback: t("createFailed"),
      }
    )
  }

  return (
    <FormDialog title={t("create")} open={open} isPending={isPending} submitText={t("createSubmit")} pendingText={t("createPending")} onClose={handleClose} onSubmit={submitCreate}>
      <TextInput label={t("colNickname")} value={nickname} error={fieldError("nickname")} required disabled={isPending} autoFocus onChange={setNickname} />
      <TextInput label={t("colUsername")} value={username} error={fieldError("username")} required disabled={isPending} onChange={setUsername} />
      <TextInput label={t("password")} type="password" value={password} error={fieldError("password")} required disabled={isPending} onChange={setPassword} />

    </FormDialog>
  )
}
