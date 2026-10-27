import type { Language } from "@/shared/api/entities"
import { translate } from "@/shared/i18n/dictionary"
import { vendorMessages } from "./i18n"

export function validateVendor(values: { name: string; country: string }, locale: Language) {
  const t = translate(vendorMessages, locale)
  const errors: Partial<Record<keyof typeof values, string>> = {}
  if (!values.name.trim()) errors.name = t("required")
  if (values.country !== "TW" && values.country !== "CN") errors.country = t("countryInvalid")
  return errors
}
