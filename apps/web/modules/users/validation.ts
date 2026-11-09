// 收 locale 讓驗證不依賴畫面, 錯誤按欄位回傳以保留在對應的輸入欄位上.

import { translate } from "@/shared/i18n/dictionary"
import type { Locale } from "@/shared/i18n/locale"
import { validateNewPassword } from "@/modules/auth/public.client"
import { usersMessages } from "./i18n"

type CreateUserValues = { username: string; nickname: string; password: string }
type CreateUserErrors = Partial<Record<keyof CreateUserValues, string>>

export function validateCreateUserValues(
  values: CreateUserValues,
  locale: Locale,
): CreateUserErrors {
  const t = translate(usersMessages, locale)
  return {
    username: values.username.trim() ? undefined : t("usernameRequired"),
    nickname: values.nickname.trim() ? undefined : t("nicknameRequired"),
    password: validateNewPassword(values.password, locale),
  }
}

export function validateResetPassword(password: string, locale: Locale): { password?: string } {
  return { password: validateNewPassword(password, locale) }
}

export function validateEditUserValues(
  values: { nickname: string },
  locale: Locale,
): { nickname?: string } {
  const t = translate(usersMessages, locale)
  return { nickname: values.nickname.trim() ? undefined : t("nicknameRequired") }
}
