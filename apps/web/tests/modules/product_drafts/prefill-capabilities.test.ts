import { describe, expect, it } from "vitest"
import { canRetryPrefill, draftValues, reloadDraftValues } from "@/modules/product_drafts/capabilities"

describe("預填重新載入", () => {
  it("僅未收集且失敗的商品可以手動執行預填", () => {
    expect(canRetryPrefill({ collecting: false, prefill_status: "failed" })).toBe(true)
    for (const prefill_status of ["idle", "disabled", "queued", "ready", "unknown"] as const) {
      expect(canRetryPrefill({ collecting: false, prefill_status })).toBe(false)
    }
    expect(canRetryPrefill({ collecting: true, prefill_status: "failed" })).toBe(false)
  })
  it("保留尚未儲存的修改並更新其他AI預填欄位", () => {
    const saved = draftValues({ name: "舊名", color: "紅色" })
    const edited = { ...saved, name: "人工名稱", year: "2020" }
    const result = reloadDraftValues(edited, saved, { name: "新名", color: "黑色" })
    expect(result.name).toBe("人工名稱")
    expect(result.year).toBe("2020")
    expect(result.color).toBe("黑色")
  })
})
