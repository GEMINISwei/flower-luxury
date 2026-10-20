import "server-only"
import { Container, ErrorState, PageHeader, Surface } from "@/shared/ui"
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
  return <Container size="lg" padded><PageHeader title={t("create")} />
    {brands.status === "success"
      ? <Surface className={styles.card}><ProductForm brands={brands.data.list_data} /></Surface>
      : <ErrorState>{t("failed")}</ErrorState>}
  </Container>
}
