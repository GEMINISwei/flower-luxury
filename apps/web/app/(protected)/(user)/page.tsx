import { redirect } from "next/navigation"
import { PRODUCTS_PATH } from "@/modules/products/manifest"

export default function HomePage() {
  redirect(PRODUCTS_PATH)
}
