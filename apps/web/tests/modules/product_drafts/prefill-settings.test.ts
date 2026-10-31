import { describe, expect, it } from "vitest"
import { parsePrefillConditions, prefillConditionState } from "@/modules/product_drafts/capabilities"

describe("AI 助手補充條件", () => {
  it("將既有補充文字拆成條件並略過空白行", () => {
    expect(parsePrefillConditions("")).toEqual([])
    expect(parsePrefillConditions("  \n\r\n")).toEqual([])
    expect(parsePrefillConditions(" 底價表示成本。\r\n\n小香表示 Chanel。 "))
      .toEqual(["底價表示成本。", "小香表示 Chanel。"])
  })

  it("補充條件依序合併並略過空白條件", () => {
    expect(prefillConditionState([], true).supplement).toBe("")
    expect(prefillConditionState([" 底價表示成本。 ", "", "  ", "小香表示 Chanel。"], true)
      .supplement).toBe("底價表示成本。\n小香表示 Chanel。")
  })

  it("補充條件共用總長度限制並保留金鑰檢查", () => {
    expect(prefillConditionState([], false)).toMatchObject({
      tooLong: false, canSave: true, canPreview: false,
    })
    expect(prefillConditionState(["文".repeat(9998), "字"], true)).toMatchObject({
      tooLong: false, canSave: true, canPreview: true,
    })
    expect(prefillConditionState(["文".repeat(9999), "字"], true)).toMatchObject({
      tooLong: true, canSave: false, canPreview: false,
    })
    expect(prefillConditionState(["🌸".repeat(10000)], true).canSave).toBe(true)
  })
})
