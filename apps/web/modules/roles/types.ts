// Entity 型別一律由後端 OpenAPI 衍生 (`Schema<"…">`), 不手寫形狀。
// 這個檔案只負責: (1) 給用到的 entity 一個貼近本畫面語意的名字, (2) 放本畫面專屬的型別。
import type { Schema } from "@/shared/api/contract"

export type RoleInfo = Schema<"RoleInfo">

/** `GET /roles/permission-options` 回傳的可勾選項目 (含後端翻好的標籤與分類)。 */
export type PermissionOption = Schema<"PermissionInfo">
