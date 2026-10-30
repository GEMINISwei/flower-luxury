import { describe, expect, it } from "vitest"
import { copyText, messageText, draftValues, draftPayload, draftValidation,
  photoOrder, moveTargets, photoSelection } from "@/modules/product_drafts/capabilities"

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
  const messages = [{ kind: "text", text: " 第一行\n第二行 " },
    { kind: "image", text: null }, { kind: "text", text: "第三行" }]
  expect(messageText(messages)).toBe(" 第一行\n第二行 \n\n第三行")
  const values = draftValues(fields)
  let copied = ""
  expect(await copyText(messages[0].text!, async (text) => { copied = text })).toBe(true)
  expect(copied).toBe(" 第一行\n第二行 ")
  expect(values).toEqual(draftValues(fields))
})

it("message_copy_failure_shows_feedback", async () => {
  expect(await copyText("text", async () => { throw new Error("denied") })).toBe(false)
})

it("messages_can_move_within_same_source", () => {
  const targets = [{ id: "a", source_key: "line:a" }, { id: "b", source_key: "line:a" },
    { id: "c", source_key: "line:b" }]
  expect(moveTargets(targets, "line:a", "a")).toEqual([targets[1]])
  expect(moveTargets(targets, "line:a", null)).toEqual(targets.slice(0, 2))
})

it("reorders photos without dropping pending or failed images", () => {
  expect(photoOrder([{ id: "a" }, { id: "b" }, { id: "c" }], "b", -1))
    .toEqual(["b", "a", "c"])
  expect(photoOrder([{ id: "a" }, { id: "b" }], "a", -1)).toEqual(["a", "b"])
})


it("照片選取在排序與刪除後保持有效", () => {
  const photos = [{ id: "a" }, { id: "b" }, { id: "c" }]
  expect(photoSelection(photos, null)).toEqual({ id: "a", index: 0 })
  expect(photoSelection(photos, "b")).toEqual({ id: "b", index: 1 })
  expect(photoSelection([photos[1], photos[0], photos[2]], "b"))
    .toEqual({ id: "b", index: 0 })
  expect(photoSelection([photos[0], photos[2]], "b")).toEqual({ id: "a", index: 0 })
  expect(photoSelection([], "b")).toEqual({ id: null, index: -1 })
})
