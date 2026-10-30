"use server"
import { apiPatch, apiPost } from "@/shared/api/request.server"
import { LINE_GROUPS_ROUTE } from "./manifest"

export async function updateGroup(id: string, enabled: boolean) {
  return apiPatch({ url: "/line/groups/{id}", params: { id }, data: { enabled },
    refresh: { path: LINE_GROUPS_ROUTE.path } })
}

export async function stopGroup(id: string) {
  return apiPost({ url: "/line/groups/{id}/stop", params: { id },
    refresh: { path: LINE_GROUPS_ROUTE.path } })
}
