import type { Language } from "@/shared/api/entities"
import { translate } from "@/shared/i18n/dictionary"
import { quoteMessages } from "./i18n"

export function validateQuote(amount: string, country: "TW" | "CN", locale: Language) {
  const t = translate(quoteMessages, locale)
  if (!/^\d+(\.\d{1,2})?$/.test(amount) || Number(amount) <= 0
      || Number(amount) > 9999999999.99) return t("amountInvalid")
  if (country === "TW" && !Number.isInteger(Number(amount))) return t("twdInteger")
}
