import {
  RegistrationPage, generateRegistrationMetadata,
} from "@/modules/registration/public.server"

export const generateMetadata = generateRegistrationMetadata

export default function Page() {
  return <RegistrationPage />
}
