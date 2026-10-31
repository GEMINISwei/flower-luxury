import type { Language } from "@/shared/api/entities"
import { translate } from "@/shared/i18n/dictionary"
import { quoteMessages } from "./i18n"

export function validateQuote(amount: string, rate: string, locale: Language) {
  const t = translate(quoteMessages, locale)
  if (!/^\d+(\.\d{1,2})?$/.test(amount) || Number(amount) <= 0
      || Number(amount) > 9999999999.99) return t("amountInvalid")
  if (!/^\d{1,10}(\.\d{1,6})?$/.test(rate) || Number(rate) <= 0) return t("rateInvalid")
  if (Math.round(Number(amount) * Number(rate)) > Number.MAX_SAFE_INTEGER) return t("amountInvalid")
}
