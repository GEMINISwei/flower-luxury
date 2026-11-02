import { expect, it } from "vitest"
import { approvalCapabilities, draftStage } from "@/modules/product_drafts/capabilities"

it("暫存狀態依收集、原圖與待加入判定", () => {
  expect(draftStage({ collecting: true, pending_count: 1 })).toBe("collecting")
  expect(draftStage({ collecting: false, processing: true, pending_count: 1 })).toBe("processing")
  expect(draftStage({ collecting: false, processing: false, pending_count: 2 })).toBe("pendingLate")
  expect(draftStage({ collecting: false, processing: false, pending_count: 0 })).toBe("waiting")
})

it("只有收集結束、原圖齊全且沒有待加入時可以建檔", () => {
  const ready = { collecting: false, pending_messages: [], photos: [{ status: "stored" }] }
  expect(approvalCapabilities(ready).canApprove).toBe(true)
  expect(approvalCapabilities({ ...ready, photos: [{ status: "ready" }, { status: "stored" }] })
    .canApprove).toBe(true)
  expect(approvalCapabilities({ ...ready, collecting: true }).canApprove).toBe(false)
  expect(approvalCapabilities({ ...ready, photos: [] }).canApprove).toBe(false)
  expect(approvalCapabilities({ ...ready, photos: [{ status: "pending" }] }).canApprove).toBe(false)
  expect(approvalCapabilities({ ...ready, photos: [{ status: "failed" }] }).canApprove).toBe(false)
  expect(approvalCapabilities({ ...ready, pending_messages: [{ id: "late" }] }).canApprove)
    .toBe(false)
})
