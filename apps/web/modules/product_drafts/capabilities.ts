import type { DraftFields, DraftValues } from "./types"

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
export function messageText(messages: { kind: string; text: string | null }[]) {
  return messages.filter((message) => message.kind === "text")
    .map((message) => message.text ?? "").join("\n\n")
}
export async function copyText(
  text: string, write = (text: string) => navigator.clipboard.writeText(text),
) {
  try { await write(text); return true } catch { return false }
}
export function moveTargets<T extends { id: string; source_key: string }>(
  drafts: T[], source: string, current: string | null,
): T[] {
  return drafts.filter((draft) => draft.source_key === source && draft.id !== current)
}
export function photoOrder(photos: { id: string }[], id: string, direction: number): string[] {
  const ids = photos.map((photo) => photo.id)
  const index = ids.indexOf(id)
  const target = index + direction
  if (index >= 0 && target >= 0 && target < ids.length) {
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
  }
  return ids
}
