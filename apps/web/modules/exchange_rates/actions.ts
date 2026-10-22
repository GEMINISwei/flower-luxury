"use server"
import { apiPatch } from "@/shared/api/request.server"

export async function updateExchangeRate(rate: string) {
  return apiPatch({ url: "/exchange-rates/settings", data: { rate },
    refresh: { path: "/admin/exchange-rates" } })
}
