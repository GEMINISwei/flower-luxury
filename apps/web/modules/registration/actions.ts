"use server"

import { apiPatch } from "@/shared/api/request.server"
import { type ActionFormData, getActionFormString } from "@/shared/api/action-form-data"
import type { ApiRequestBody } from "@/shared/api/contract"
import { REGISTRATION_PATH } from "./manifest"

export async function updateRegistrationKey(
  formData: ActionFormData<ApiRequestBody<"/registration/settings", "patch">>,
) {
  return apiPatch({
    url: "/registration/settings",
    data: { registration_key: getActionFormString(formData, "registration_key") },
    refresh: { path: REGISTRATION_PATH },
  })
}
