import "server-only"
import { getT } from "@/shared/i18n/locale.server"
import { registrationMessages } from "@/modules/registration/public.client"
import SignupForm from "./ui/SignupForm"

export async function generateMetadata() {
  return { title: (await getT(registrationMessages))("signupTitle") }
}

export default function SignupPage() {
  return <SignupForm />
}
