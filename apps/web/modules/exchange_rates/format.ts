import { validateRate } from "./validation"

export function formatRate(value: string | null): string {
  if (value === null) return ""
  if (validateRate(value, "en")) return value
  // 以十進位字串四捨五入, 避免 1.005 等值的浮點數誤差.
  const [integer, fraction = ""] = value.split(".")
  const digits = fraction.padEnd(3, "0")
  const cents = Number(integer) * 100 + Number(digits.slice(0, 2))
    + (Number(digits[2]) >= 5 ? 1 : 0)
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`
}
