"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, ConfirmDialog, Container, ErrorState, Flex, ListTableCard, PageHeader,
  StatusBadge, TableRow, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { vendorMessages } from "../i18n"
import type { VendorInfo } from "../types"
import { deleteVendor } from "../actions"
import VendorDialog from "./VendorDialog"
import styles from "./vendors.module.css"

export default function VendorsView({ vendors, errorMessage }: {
  vendors: VendorInfo[]; errorMessage: string
}) {
  const t = useT(vendorMessages)
  const router = useRouter()
  const [editor, setEditor] = useState<VendorInfo | "new" | null>(null)
  const [removing, setRemoving] = useState<VendorInfo | null>(null)
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function remove() {
    if (!removing) return
    submit(() => deleteVendor(removing.id), {
      onSuccess: () => { setRemoving(null); router.refresh() }, onError: setError,
    })
  }
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={<Button onClick={() => setEditor("new")}>{t("create")}</Button>} />
    {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
    {!removing && error && <p role="alert">{error}</p>}
    <ListTableCard headers={[t("name"), t("country"), t("note"), t("status"), t("actions")]}
      isEmpty={!vendors.length} emptyText={t("empty")}>
      {vendors.map((vendor) => <TableRow key={vendor.id}>
        <td data-label={t("name")}>{vendor.name}</td>
        <td data-label={t("country")}>{t(vendor.country)}</td>
        <td data-label={t("note")}>{vendor.note || "—"}</td>
        <td data-label={t("status")}><StatusBadge label={t(vendor.is_active ? "active" : "inactive")}
          variant={vendor.is_active ? "success" : "muted"} /></td>
        <td data-label={t("actions")}><Flex gap={2} className={styles.actions}>
          <Button variant="outlined" disabled={isPending} onClick={() => setEditor(vendor)}>
            {t("edit")}</Button>
          <Button variant="outlined" disabled={isPending}
            onClick={() => { setError(""); setRemoving(vendor) }}>
            {t("delete")}</Button>
        </Flex></td>
      </TableRow>)}
    </ListTableCard>
    {editor && <VendorDialog key={editor === "new" ? "new" : editor.id}
      vendor={editor === "new" ? undefined : editor} onClose={() => setEditor(null)} />}
    <ConfirmDialog title={t("delete")} open={Boolean(removing)} isPending={isPending}
      confirmText={t("delete")} onClose={() => setRemoving(null)} onConfirm={remove}>
      <p>{removing?.name}</p><p>{t("confirm")}</p>
      {error && <p role="alert">{error}</p>}
    </ConfirmDialog>
  </Container>
}
