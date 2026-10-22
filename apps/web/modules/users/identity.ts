import { hasAllPermission } from "@/shared/access/permissions"

export function accountIdentity(permissions: readonly string[]): "manager" | "staff" {
  return hasAllPermission(permissions) ? "manager" : "staff"
}
