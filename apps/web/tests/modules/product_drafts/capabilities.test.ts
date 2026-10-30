import { describe, expect, it } from "vitest"
import { copyText, draftValues, draftPayload, draftValidation,
  photoSelection } from "@/modules/product_drafts/capabilities"

const fields = { name: "", brand_id: null, category: null, cost_price: null }

describe("draft_fields_remain_user_controlled", () => {
  it("allows incomplete values, preserves zero and rejects invalid numbers", () => {
    const values = draftValues(fields)
    expect(draftPayload(values).cost_price).toBeNull()
    expect(draftValidation(values, false)).toEqual([])
    expect(draftValidation(values, true)).toEqual(["name", "brand_id", "category", "cost_price"])
    expect(draftPayload({ ...values, cost_price: "0" }).cost_price).toBe(0)
    expect(draftValidation({ ...values, year: "1.5", cost_price: "-1" }, false))
      .toEqual(["year", "cost_price"])
    expect(draftValidation({ ...values, year: " ", cost_price: " " }, false)).toEqual([])
  })
})

it("click_message_copies_full_text", async () => {
  const text = " 第一行\n第二行 "
  let copied = ""
  expect(await copyText(text, async (value) => { copied = value })).toBe(true)
  expect(copied).toBe(text)
})

it("message_copy_failure_shows_feedback", async () => {
  expect(await copyText("text", async () => { throw new Error("denied") })).toBe(false)
})

it("照片選取在刪除後保持有效", () => {
  const photos = [{ id: "a" }, { id: "b" }, { id: "c" }]
  expect(photoSelection(photos, null)).toEqual({ id: "a", index: 0 })
  expect(photoSelection(photos, "b")).toEqual({ id: "b", index: 1 })
  expect(photoSelection([photos[0], photos[2]], "b")).toEqual({ id: "a", index: 0 })
  expect(photoSelection([], "b")).toEqual({ id: null, index: -1 })
})
