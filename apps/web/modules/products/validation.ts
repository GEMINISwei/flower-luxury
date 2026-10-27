import type { Language } from "@/shared/api/entities"
import { translate } from "@/shared/i18n/dictionary"
import { productMessages } from "./i18n"

type FormValues = {
  name: string; brand_id: string; category: string; cost_price: string; year: string
}

export function validateProduct(values: FormValues, locale: Language) {
  const t = translate(productMessages, locale)
  const errors: Partial<Record<keyof FormValues, string>> = {}
  for (const field of ["name", "brand_id", "category"] as const) {
    if (!values[field].trim()) errors[field] = t("required")
  }
  if (!validInteger(values.cost_price, 0, 2147483647)) {
    errors.cost_price = t("costInvalid")
  }
  if (values.year && !validInteger(values.year, 1, 9999)) {
    errors.year = t("yearInvalid")
  }
  return errors
}

function validInteger(value: string, min: number, max: number): boolean {
  const number = Number(value)
  return Boolean(value.trim()) && Number.isInteger(number) && number >= min && number <= max
}

export function validatePhotoBatch(
  files: readonly { size: number; name: string; type: string }[], locale: Language,
): string | undefined {
  const t = translate(productMessages, locale)
  if (!files.length || files.some((file) => file.size <= 0)
      || files.reduce((sum, file) => sum + file.size, 0) > 15 * 1024 * 1024) {
    return t("batchInvalid")
  }
  if (files.some((file) => !/\.(jpe?g|png|webp|heic|heif)$/i.test(file.name))) {
    return t("formatInvalid")
  }
}

export function validateReturnReason(reason: string, locale: Language): string | undefined {
  if (!reason.trim()) return translate(productMessages, locale)("required")
}
