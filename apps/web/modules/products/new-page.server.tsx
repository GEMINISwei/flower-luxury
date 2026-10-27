import "server-only"
import { ErrorState, FormPageShell, Surface } from "@/shared/ui"
import { getBrandOptions } from "@/modules/brands/public.server"
import { getT } from "@/shared/i18n/locale.server"
import { productMessages } from "./i18n"
import ProductForm from "./ui/ProductForm"
import styles from "./ui/catalog.module.css"

export async function generateMetadata() {
  return { title: (await getT(productMessages))("create") }
}
export default async function NewProductPage() {
  const t = await getT(productMessages)
  const brands = await getBrandOptions()
  return <FormPageShell title={t("create")} subtitle={t("createSubtitle")}
    actions={null} backHref="/products" backLabel={t("back")}>
    {brands.status === "success"
      ? <Surface className={`${styles.card} ${styles.formCard}`}><ProductForm brands={brands.data.list_data} /></Surface>
      : <ErrorState>{t("failed")}</ErrorState>}
  </FormPageShell>
}
