"use client"

import { type FormEvent, useState } from "react"
import { FormDialog, SelectInput, TextInput, useActionSubmit, useActiveStatusOptions } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { usersMessages } from "../i18n"
import { updateUser } from "../actions"
import { getEditableUserFields } from "../capabilities"
import type { CurrentUser, RoleInfo, UserInfo } from "../types"

type EditUserDialogProps = {
  user: UserInfo | null
  onClose: () => void
  onSuccess: (message: string) => void
  onError: (message: string) => void
  currentUser: CurrentUser | null
  roles: RoleInfo[]
}

export default function EditUserDialog({
  user,
  onClose,
  onSuccess,
  onError,
  currentUser,
  roles,
}: EditUserDialogProps) {
  const t = useT(usersMessages)
  const statusOptions = useActiveStatusOptions()
  const [nickname, setNickname] = useState(user?.nickname ?? "")
  const [isDisabled, setIsDisabled] = useState(user?.is_disabled ?? false)
  const { isPending, submit, fieldError } = useActionSubmit()
  const { canToggleStatus } = user
    ? getEditableUserFields(user, currentUser?.id, roles, false)
    : { canToggleStatus: false }

  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!user || !nickname.trim()) {
      onError(t("nicknameRequired"))
      return
    }

    submit(
      () => updateUser(user.id, {
        nickname: nickname.trim(),
        is_disabled: isDisabled,
      }),
      {
        onSuccess: () => onSuccess(t("userUpdated")),
        onError,
        errorFallback: t("updateFailed"),
      }
    )
  }

  return (
    <FormDialog
      title={t("editTitle")}
      open={user !== null}
      isPending={isPending}
      submitText={t("editSubmit")}
      pendingText={t("editPending")}
      onClose={onClose}
      onSubmit={submitEdit}
    >
      <TextInput label={t("colUsername")} value={user?.username ?? ""} disabled />
      <TextInput
        label={t("colNickname")}
        value={nickname}
        error={fieldError("nickname")}
        required
        disabled={isPending}
        autoFocus
        onChange={setNickname}
      />
      {canToggleStatus && (
        <SelectInput
          label={t("colStatus")}
          value={isDisabled ? "disabled" : "active"}
          error={fieldError("is_disabled")}
          disabled={isPending}
          options={statusOptions}
          onChange={(value) => setIsDisabled(value === "disabled")}
        />
      )}
    </FormDialog>
  )
}
