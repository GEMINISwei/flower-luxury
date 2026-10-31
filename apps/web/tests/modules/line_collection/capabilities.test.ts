import { expect, it } from "vitest"
import { groupCapabilities } from "@/modules/line_collection/capabilities"

it("left_group_cannot_be_enabled", () => {
  expect(groupCapabilities({ joined: false, enabled: false }).canToggle).toBe(false)
  expect(groupCapabilities({ joined: true, enabled: false }).canToggle).toBe(true)
  expect(groupCapabilities({ joined: true, enabled: true }).nextEnabled).toBe(false)
})


it("群組狀態依加入啟用與收集情況提供標籤與樣式", () => {
  const disabled = groupCapabilities({ joined: false, enabled: false, collecting: false })
  expect(disabled.bot).toEqual({ label: "left", variant: "muted" })
  expect(disabled.collection).toEqual({ label: "disabled", variant: "muted" })
  const waiting = groupCapabilities({ joined: true, enabled: true, collecting: false })
  expect(waiting.bot).toEqual({ label: "joined", variant: "success" })
  expect(waiting.collection).toEqual({ label: "waiting", variant: "warning" })
  expect(groupCapabilities({ joined: true, enabled: true, collecting: true }).collection)
    .toEqual({ label: "collecting", variant: "success" })
  expect(groupCapabilities({ joined: true, enabled: false, collecting: true }).collection)
    .toEqual({ label: "disabled", variant: "muted" })
})
