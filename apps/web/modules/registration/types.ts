import type { ApiRequestBody } from "@/shared/api/contract"

export type SignupValues = ApiRequestBody<"/registration/signup", "post"> & {
  confirm_password: string
}
export type SignupErrors = Partial<Record<keyof SignupValues, string>>
