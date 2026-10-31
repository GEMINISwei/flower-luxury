"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { useRouter } from "next/navigation"
import { Button, ConfirmDialog, Container, ErrorState, Flex, ListTableCard, PageHeader,
  ICON_SIZE, StatusBadge, TableRow, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { vendorMessages } from "../i18n"
import { vendorRemovalAction } from "../capabilities"
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
  const removalAction = removing ? vendorRemovalAction(removing) : "delete"
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={[{ label: t("create"), icon: <Plus size={ICON_SIZE.md} />,
        primary: true, onClick: () => setEditor("new") }]} />
    {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
    {!removing && error && <p role="alert">{error}</p>}
    <div className={styles.list}><ListTableCard headers={[t("name"), t("note"), t("status"), t("actions")]}
      isEmpty={!vendors.length} emptyText={t("empty")}>
      {vendors.map((vendor) => {
        const action = vendorRemovalAction(vendor)
        return <TableRow key={vendor.id}>
        <td data-label={t("name")}>{vendor.name}</td>
        <td data-label={t("note")}>{vendor.note || "—"}</td>
        <td data-label={t("status")}><StatusBadge label={t(vendor.is_active ? "active" : "inactive")}
          variant={vendor.is_active ? "success" : "muted"} /></td>
        <td data-label={t("actions")}><Flex gap={2} className={styles.actions}>
          <Button variant="outlined" disabled={isPending} onClick={() => setEditor(vendor)}>
            {t("edit")}</Button>
          {action && <Button variant="outlined" disabled={isPending}
            onClick={() => { setError(""); setRemoving(vendor) }}>
            {t(action)}</Button>}
        </Flex></td>
      </TableRow>})}
    </ListTableCard></div>
    {editor && <VendorDialog key={editor === "new" ? "new" : editor.id}
      vendor={editor === "new" ? undefined : editor} onClose={() => setEditor(null)} />}
    <ConfirmDialog title={t(removalAction ?? "delete")} open={Boolean(removing)} isPending={isPending}
      confirmText={t(removalAction ?? "delete")} onClose={() => setRemoving(null)} onConfirm={remove}>
      <p>{removing?.name}</p><p>{t(removalAction === "deactivate" ? "confirmDeactivate" : "confirmDelete")}</p>
      {error && <p role="alert">{error}</p>}
    </ConfirmDialog>
  </Container>
}
