import { expect, it } from "vitest"
import { groupCapabilities } from "@/modules/line_collection/capabilities"

it("left_group_cannot_be_enabled", () => {
  expect(groupCapabilities({ joined: false, enabled: false }).canToggle).toBe(false)
  expect(groupCapabilities({ joined: true, enabled: false }).canToggle).toBe(true)
  expect(groupCapabilities({ joined: true, enabled: true }).nextEnabled).toBe(false)
})

it("群組啟用即顯示收集中，停用顯示已停用", () => {
  const left = groupCapabilities({ joined: false, enabled: false })
  expect(left.bot).toEqual({ label: "left", variant: "muted" })
  expect(left.collection).toEqual({ label: "disabled", variant: "muted" })
  const enabled = groupCapabilities({ joined: true, enabled: true })
  expect(enabled.bot).toEqual({ label: "joined", variant: "success" })
  expect(enabled.collection).toEqual({ label: "collecting", variant: "success" })
  expect(groupCapabilities({ joined: true, enabled: false }).collection)
    .toEqual({ label: "disabled", variant: "muted" })
})
