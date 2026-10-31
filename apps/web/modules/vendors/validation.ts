import type { Language } from "@/shared/api/entities"
import { translate } from "@/shared/i18n/dictionary"
import { vendorMessages } from "./i18n"

export function validateVendor(values: { name: string }, locale: Language) {
  const t = translate(vendorMessages, locale)
  const errors: Partial<Record<keyof typeof values, string>> = {}
  if (!values.name.trim()) errors.name = t("required")
  return errors
}
