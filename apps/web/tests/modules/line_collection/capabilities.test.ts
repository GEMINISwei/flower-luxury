import { expect, it } from "vitest"
import { groupCapabilities } from "@/modules/line_collection/capabilities"

it("left_group_cannot_be_enabled", () => {
  expect(groupCapabilities({ joined: false, enabled: false }).canToggle).toBe(false)
  expect(groupCapabilities({ joined: true, enabled: false }).canToggle).toBe(true)
  expect(groupCapabilities({ joined: true, enabled: true }).nextEnabled).toBe(false)
})
