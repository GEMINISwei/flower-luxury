export function formatDateTime(value: string, timeZone: string): string {
  // 只取數字欄位並固定組字, 避免 Node 與瀏覽器的 ICU 分隔符不同而造成 hydration mismatch.
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone, calendar: "gregory", numberingSystem: "latn", hourCycle: "h23",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).formatToParts(new Date(value))
  const fields = Object.fromEntries(parts.map(({ type, value }) => [type, value]))
  return `${fields.year}/${fields.month}/${fields.day} ${fields.hour}:${fields.minute}:${fields.second}`
}
