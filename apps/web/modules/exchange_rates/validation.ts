import type { Language } from "@/shared/api/entities"
import { translate } from "@/shared/i18n/dictionary"
import { exchangeMessages } from "./i18n"

export function validateRate(value: string, locale: Language): string | undefined {
  if (!/^\d{1,10}(\.\d{1,6})?$/.test(value) || Number(value) <= 0) {
    return translate(exchangeMessages, locale)("invalid")
  }
}
