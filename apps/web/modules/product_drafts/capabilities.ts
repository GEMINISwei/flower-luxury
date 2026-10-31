import type { DraftFields, DraftValues, MessageInfo } from "./types"

export function draftTextMessages(messages: MessageInfo[]): MessageInfo[] {
  return messages.filter((message) => message.kind === "text")
}

const FIELDS = ["name", "brand_id", "category", "model_name", "serial_number",
  "color", "year", "cost_price", "internal_note"] as const
export function draftValues(fields: DraftFields): DraftValues {
  return Object.fromEntries(FIELDS.map((key) => [key, String(fields[key] ?? "")])) as DraftValues
}
export function draftPayload(values: DraftValues): DraftFields {
  const strings = Object.fromEntries(
    FIELDS.map((key) => [key, values[key].trim() ? values[key] : null]))
  return { ...strings, category: (values.category || null) as DraftFields["category"],
    year: values.year.trim() ? Number(values.year) : null,
    cost_price: values.cost_price.trim() ? Number(values.cost_price) : null }
}
function validNumber(value: string, min: number, max: number) {
  const number = Number(value)
  return Number.isInteger(number) && number >= min && number <= max
}
export function draftValidation(values: DraftValues, approving: boolean): (keyof DraftValues)[] {
  const errors: (keyof DraftValues)[] = []
  if (approving) for (const key of ["name", "brand_id", "category"] as const) {
    if (!values[key].trim()) errors.push(key)
  }
  if (values.year.trim() && !validNumber(values.year, 1, 9999)) errors.push("year")
  if ((approving && !values.cost_price.trim())
      || (values.cost_price.trim() && !validNumber(values.cost_price, 0, 2147483647))) {
    errors.push("cost_price")
  }
  return errors
}
export async function copyText(
  text: string, write = (text: string) => navigator.clipboard.writeText(text),
) {
  try { await write(text); return true } catch { return false }
}
export function photoSelection(photos: { id: string }[], selected: string | null) {
  const found = photos.findIndex((photo) => photo.id === selected)
  const index = found >= 0 ? found : Math.min(0, photos.length - 1)
  return { id: photos[index]?.id ?? null, index }
}
