import { beforeEach, expect, it, vi } from "vitest"
import type { ApiResponse } from "@/shared/api/contract"

const state = vi.hoisted(() => ({ token: "jwt" as string | undefined }))
const mocks = vi.hoisted(() => ({
  fetch: vi.fn(), clear: vi.fn(), refresh: vi.fn(),
  redirect: vi.fn((url: string) => {
    throw Object.assign(new Error("redirect"), { digest: `NEXT_REDIRECT;replace;${url}` })
  }),
}))
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => state.token ? { value: state.token } : undefined }),
  headers: async () => new Headers({ "x-request-id": "upload-1", "x-real-ip": "192.0.2.1" }),
}))
vi.mock("next/navigation", () => ({ redirect: mocks.redirect }))
vi.mock("next/cache", () => ({ revalidatePath: mocks.refresh, revalidateTag: vi.fn() }))
vi.mock("@/shared/i18n/locale.server", () => ({ getLocale: async () => "en" }))
vi.mock("@/shared/session/access-token.server", () => ({ clearAccessTokenCookie: mocks.clear }))
vi.stubGlobal("fetch", mocks.fetch)

const { apiUpload: typedUpload } = await import("@/shared/api/request.server")
const upload = typedUpload as unknown as (request: {
  url: string; params: Record<string, string>; data: FormData; refresh?: { path: string }
}) => Promise<ApiResponse>

beforeEach(() => { vi.clearAllMocks(); state.token = "jwt" })
function request() {
  const data = new FormData()
  data.append("files", new File(["photo"], "photo.png", { type: "image/png" }))
  return { url: "/things/{id}/files", params: { id: "a/b" }, data, refresh: { path: "/things" } }
}
function respond(status: number, body: unknown) {
  mocks.fetch.mockResolvedValueOnce(new Response(JSON.stringify(body), { status }))
}

it("檔案上傳保留 FormData 並沿用登入語系追蹤與真實 IP，不手動設定 boundary", async () => {
  const input = request()
  respond(200, { count: 1 })
  expect((await upload(input)).status).toBe("success")
  const [url, init] = mocks.fetch.mock.calls[0] as [string, RequestInit]
  const headers = new Headers(init.headers)
  expect(url).toBe("http://api:8000/api/things/a%2Fb/files")
  expect(init.method).toBe("POST")
  expect(init.body).toBe(input.data)
  expect(headers.get("Content-Type")).toBeNull()
  expect(headers.get("Cookie")).toBe("access_token=jwt")
  expect(headers.get("Accept-Language")).toBe("en")
  expect(headers.get("X-Request-ID")).toBe("upload-1")
  expect(headers.get("X-Real-IP")).toBe("192.0.2.1")
  expect(mocks.refresh).toHaveBeenCalledWith("/things")
})

it("上傳缺少 token 時不送請求並清理 cookie 導回登入頁", async () => {
  state.token = undefined
  await expect(upload(request())).rejects.toMatchObject({ digest: expect.stringContaining("NEXT_REDIRECT") })
  expect(mocks.fetch).not.toHaveBeenCalled()
  expect(mocks.clear).toHaveBeenCalled()
  expect(mocks.redirect).toHaveBeenCalledWith("/login?reason=session-expired")
})

it("上傳收到 401 時清理 cookie 並保留 Session 過期導向", async () => {
  respond(401, { detail: "expired" })
  await expect(upload(request())).rejects.toMatchObject({ digest: expect.stringContaining("NEXT_REDIRECT") })
  expect(mocks.clear).toHaveBeenCalled()
  expect(mocks.redirect).toHaveBeenCalledWith("/login?reason=session-expired")
  expect(mocks.refresh).not.toHaveBeenCalled()
})

it("上傳解析欄位錯誤且失敗不刷新快取", async () => {
  respond(422, { detail: [{ loc: ["body", "files"], msg: "Invalid file", type: "value_error" }] })
  const result = await upload(request())
  expect(result.status).toBe("failure")
  if (result.status !== "failure") throw new Error("unreachable")
  expect(result.data.fieldErrors).toBeDefined()
  expect(mocks.refresh).not.toHaveBeenCalled()
})

it("上傳連線或無效 JSON 錯誤沿用共用錯誤回應", async () => {
  mocks.fetch.mockRejectedValueOnce(new TypeError("offline"))
  expect((await upload(request())).status).toBe("error")
  mocks.fetch.mockResolvedValueOnce(new Response("invalid", { status: 502 }))
  expect((await upload(request())).status).toBe("error")
  expect(mocks.refresh).not.toHaveBeenCalled()
})
