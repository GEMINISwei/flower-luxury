import fs from "node:fs"
import { describe, expect, it } from "vitest"
import manifest from "@/app/manifest"

const theme = fs.readFileSync(new URL("../../app/theme.css", import.meta.url), "utf8")

function color(name: string) {
  const value = theme.match(new RegExp(`--color-${name}:\\s*(#[a-f0-9]{6})`, "i"))?.[1]
  expect(value, `主題應定義 ${name}`).toBeDefined()
  return value!
}

function luminance(hex: string) {
  const channels = hex.slice(1).match(/../g)!.map((channel) => {
    const value = parseInt(channel, 16) / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
}

describe("小花精品淺色主題", () => {
  it.each([
    ["text-body", "bg-app"],
    ["text-secondary", "surface-card"],
    ["text-muted", "surface-card"],
    ["primary", "surface-card"],
    ["on-primary-container", "primary-container"],
    ["text-on-primary", "action-primary"],
    ["success-fg", "success-bg"],
    ["warning-fg", "warning-bg"],
    ["danger-fg", "danger-bg"],
    ["info-fg", "info-bg"],
  ])("主題文字與對應背景的對比至少為 4.5：%s / %s", (foreground, background) => {
    const values = [luminance(color(foreground)), luminance(color(background))]
    expect((Math.max(...values) + 0.05) / (Math.min(...values) + 0.05)).toBeGreaterThanOrEqual(4.5)
  })

  it("manifest 與淺色主題背景一致", () => {
    expect(theme).toMatch(/color-scheme:\s*light\s*;/)
    expect(manifest().theme_color?.toLowerCase()).toBe(color("bg-app").toLowerCase())
  })
})
