import { validateNewPassword } from "@/modules/auth/public.client"
import { translate } from "@/shared/i18n/dictionary"
import type { Locale } from "@/shared/i18n/locale"
import { registrationMessages } from "./i18n"
import type { SignupErrors, SignupValues } from "./types"

export function validateRegistrationKey(value: string, locale: Locale): string | undefined {
  const length = Array.from(value).length
  if (length < 8 || length > 128) return translate(registrationMessages, locale)("keyLength")
}

export function validateSignup(values: SignupValues, locale: Locale): SignupErrors {
  const t = translate(registrationMessages, locale)
  const errors: SignupErrors = {}
  if (!values.username.trim()) errors.username = t("usernameRequired")
  if (!values.nickname.trim()) errors.nickname = t("nicknameRequired")
  errors.password = validateNewPassword(values.password, locale)
  if (values.confirm_password !== values.password) errors.confirm_password = t("passwordMismatch")
  if (!values.registration_key) errors.registration_key = t("keyRequired")
  if (Array.from(values.registration_key).length > 128) errors.registration_key = t("keyTooLong")
  return errors
}
