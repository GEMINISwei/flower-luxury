import { expect, it } from "vitest"
import { accountIdentity } from "@/modules/users/identity"

it("依管理權限顯示店長或員工", () => {
  expect(accountIdentity(["*"])).toBe("manager")
  expect(accountIdentity([])).toBe("staff")
})
