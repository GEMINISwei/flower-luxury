import "server-only"
import { cookies, headers } from "next/headers"
import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"
import { buildRequestHeaders } from "@/shared/api/headers"
import { parseErrorDetail } from "@/shared/api/payload"
import { getLocale } from "@/shared/i18n/locale.server"
import { translate } from "@/shared/i18n/dictionary"
import { ACCESS_TOKEN_COOKIE, loginUrl } from "@/shared/session/login-contract"
import type { ApiResponse } from "@/shared/api/contract"
import { validatePhotoBatch } from "./validation"
import { productMessages } from "./i18n"
import { PRODUCTS_PATH } from "./manifest"

export async function sendPhotoBatch(id: string, data: FormData): Promise<ApiResponse> {
  const locale = await getLocale()
  const t = translate(productMessages, locale)
  const files = data.getAll("files").filter((file): file is File => file instanceof File)
  const error = validatePhotoBatch(files, locale)
  if (error) return { status: "failure", code: 422, data: { detail: error }, message: error }
  const token = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value
  if (!token) redirect(loginUrl())
  const incoming = await headers()
  const body = new FormData()
  files.forEach((file) => body.append("files", file))
  let response: Response
  try {
    response = await fetch(
      `${process.env.API_URL || "http://api:8000"}/api/products/${encodeURIComponent(id)}/photos`,
      { method: "POST", body, headers: buildRequestHeaders({
        locale, authRequired: true, token,
        requestId: incoming.get("x-request-id") ?? undefined,
        clientIp: incoming.get("x-real-ip") ?? undefined,
      }) },
    )
  } catch {
    return { status: "error", code: 999, data: { detail: t("actionFailed") }, message: "Upload failed" }
  }
  if (response.status === 401) redirect(loginUrl())
  const result = await response.json()
  if (!response.ok) {
    return { status: "failure", code: response.status,
      data: { detail: parseErrorDetail(result.detail).message }, message: "Upload failed" }
  }
  revalidatePath(PRODUCTS_PATH)
  revalidatePath(`${PRODUCTS_PATH}/${id}`)
  return { status: "success", code: response.status, data: result, message: "Uploaded" }
}
