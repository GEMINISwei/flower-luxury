import { describe, expect, it } from "vitest"
import { validateRegistrationKey, validateSignup } from "@/modules/registration/validation"

const values = {
  username: "manager", nickname: "店長", password: "password123",
  confirm_password: "password123", registration_key: "shop-manager-key",
}

describe("公開註冊", () => {
  it("註冊資料缺漏與密碼不符會顯示對應語系錯誤", () => {
    for (const locale of ["zh", "en"] as const) {
      const errors = validateSignup({
        username: " ", nickname: "", password: "short",
        confirm_password: "different", registration_key: "",
      }, locale)
      for (const field of Object.keys(values)) {
        expect(errors[field as keyof typeof errors]).toBeTruthy()
      }
      expect(errors.username).toBe(locale === "zh" ? "請輸入帳號" : "Username is required")
    }
  })

  it("正確註冊資料沒有錯誤", () => {
    expect(Object.values(validateSignup(values, "zh")).filter(Boolean)).toEqual([])
  })

  it("註冊碼須為 8 至 128 個字元", () => {
    expect(validateRegistrationKey("short", "zh")).toBeTruthy()
    expect(validateRegistrationKey("a".repeat(129), "en")).toBeTruthy()
    expect(validateRegistrationKey("a".repeat(8), "zh")).toBeUndefined()
    expect(validateRegistrationKey("a".repeat(128), "en")).toBeUndefined()
  })

  it("註冊碼不會自動去除空白，密碼以 bytes 檢查上限", () => {
    expect(Object.values(validateSignup({ ...values, password: "花".repeat(25) }, "zh")))
      .toContain("不可超過 72 bytes")
    expect(validateRegistrationKey(" abcdef ", "zh")).toBeUndefined()
  })
})
