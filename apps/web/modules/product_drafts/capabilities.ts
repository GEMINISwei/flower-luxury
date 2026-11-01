import type { DraftFields, DraftValues, MessageInfo } from "./types"

export function draftStage(draft: {
  collecting: boolean; processing?: boolean; needs_confirmation?: boolean
}) {
  if (draft.needs_confirmation) return "needsConfirmation"
  if (draft.collecting) return "collecting"
  if (draft.processing) return "processing"
  return "waiting"
}

export function draftQueueHref(id?: string, source?: string, created?: string) {
  const query = new URLSearchParams()
  if (source) query.set("source_key", source)
  if (created) query.set("created", created)
  return `/product-drafts${id ? `/${id}` : ""}${query.size ? `?${query}` : ""}`
}

export function draftTextMessages(messages: MessageInfo[]): MessageInfo[] {
  return messages.filter((message) => message.kind === "text")
}

const FIELDS = ["name", "brand_id", "category", "model_name", "serial_number",
  "color", "year", "cost_price", "internal_note"] as const
export function draftValues(fields: DraftFields): DraftValues {
  return Object.fromEntries(FIELDS.map((key) => [key, String(fields[key] ?? "")])) as DraftValues
}
export function reloadDraftValues(current: DraftValues, saved: DraftValues,
  latest: DraftFields): DraftValues {
  const updated = draftValues(latest)
  return Object.fromEntries(FIELDS.map((key) => [key,
    current[key] === saved[key] ? updated[key] : current[key]])) as DraftValues
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

export function parsePrefillConditions(supplement: string): string[] {
  return supplement.split(/\r?\n/).map((condition) => condition.trim()).filter(Boolean)
}

export function prefillConditionState(conditions: string[], configured: boolean) {
  const supplement = conditions.map((condition) => condition.trim()).filter(Boolean).join("\n")
  const tooLong = Array.from(supplement).length > 10000
  return { supplement, tooLong, canSave: !tooLong, canPreview: configured && !tooLong }
}
