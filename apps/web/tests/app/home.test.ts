import { expect, it, vi } from "vitest"
import HomePage from "@/app/(protected)/(user)/page"

vi.mock("next/navigation", () => ({
  redirect: vi.fn(() => { throw new Error("redirect") }),
}))

it("根網址直接導向商品列表", async () => {
  const { redirect } = await import("next/navigation")
  await expect(HomePage()).rejects.toThrow("redirect")
  expect(redirect).toHaveBeenCalledWith("/products")
})
