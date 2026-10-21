import { afterEach, expect, it, vi } from "vitest"
import { formatDateTime } from "@/shared/i18n/date-time"

afterEach(() => vi.restoreAllMocks())

it("日期時間依指定時區顯示完整年月日時分秒", () => {
  const timestamp = "2026-10-20T16:01:59Z"
  expect(formatDateTime(timestamp, "Asia/Taipei")).toBe("2026/10/21 00:01:59")
  expect(formatDateTime(timestamp, "UTC")).toBe("2026/10/20 16:01:59")
  expect(formatDateTime("2026-12-31T16:00:00Z", "Asia/Taipei"))
    .toBe("2027/01/01 00:00:00")
})

it("不同 ICU 分隔符與排列仍產生相同日期文字", () => {
  const timestamp = "2026-10-20T16:01:59Z"
  const parts: Intl.DateTimeFormatPart[] = [
    { type: "year", value: "2026" }, { type: "literal", value: "/" },
    { type: "month", value: "10" }, { type: "literal", value: "/" },
    { type: "day", value: "21" }, { type: "literal", value: " " },
    { type: "hour", value: "00" }, { type: "literal", value: ":" },
    { type: "minute", value: "01" }, { type: "literal", value: ":" },
    { type: "second", value: "59" },
  ]
  vi.spyOn(Intl.DateTimeFormat.prototype, "formatToParts")
    .mockReturnValueOnce(parts)
    .mockReturnValueOnce(parts.toReversed().map((part) =>
      part.type === "literal" ? { ...part, value: "\u202f\u00a0\u200e" } : part,
    ))

  const serverText = formatDateTime(timestamp, "Asia/Taipei")
  const browserText = formatDateTime(timestamp, "Asia/Taipei")
  expect(serverText).toBe("2026/10/21 00:01:59")
  expect(browserText).toBe(serverText)
})
