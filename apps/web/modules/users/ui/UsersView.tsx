"use client"

import { useState } from "react"
import { Container, ListPageHeader, Notify, useListFeedback } from "@/shared/ui"
import type { ApiListMeta } from "@/shared/api/response"
import { useT } from "@/shared/i18n/context"
import { usersMessages } from "../i18n"
import type { CurrentUser, RoleInfo, UserFilters, UserInfo } from "../types"
import CreateUserDialog from "./CreateUserDialog"
import EditUserDialog from "./EditUserDialog"
import ResetPasswordDialog from "./ResetPasswordDialog"
import UsersTable from "./UsersTable"
import UsersFilterDialog from "./UsersFilterDialog"

type Dialog = "create" | "edit" | "reset" | null

type UsersViewProps = {
  users: UserInfo[]
  meta: ApiListMeta
  seq: number
  limit: number
  currentUser: CurrentUser | null
  roles: RoleInfo[]
  errorMessage: string
  rolesErrorMessage: string
  filters: UserFilters
}

export default function UsersView({
  users,
  meta,
  seq,
  limit,
  currentUser,
  roles,
  errorMessage,
  rolesErrorMessage,
  filters,
}: UsersViewProps) {
  const t = useT(usersMessages)
  const showReset = meta.hasPrevious
  const [dialog, setDialog] = useState<Dialog>(null)
  const [selectedUser, setSelectedUser] = useState<UserInfo | null>(null)
  const [filterDialogOpen, setFilterDialogOpen] = useState(false)

  function closeSelectedDialog() {
    setDialog(null)
    setSelectedUser(null)
  }

  function openCreate() { setDialog("create") }

  function openFor(user: UserInfo, nextDialog: Exclude<Dialog, "create" | null>) {
    setSelectedUser(user)
    setDialog(nextDialog)
  }

  const { notify, closeNotify, handleSuccess, handleError } = useListFeedback(closeSelectedDialog)

  return (
    <Container size="lg" padded>
      <ListPageHeader
        title={t("heading")}
        subtitle={t("subtitle")}
        showReset={showReset}
        onFilter={() => setFilterDialogOpen(true)}
        createAction={{ label: t("create"), onClick: openCreate }}
      />

      <UsersTable
        users={users}
        roles={roles}
        meta={meta}
        seq={seq}
        limit={limit}
        currentUser={currentUser}
        errorMessage={errorMessage}
        rolesErrorMessage={rolesErrorMessage}
        onEdit={(user) => openFor(user, "edit")}
        onResetPassword={(user) => openFor(user, "reset")}
      />

      <CreateUserDialog
        open={dialog === "create"}
        onClose={() => setDialog(null)}
        onSuccess={handleSuccess}
        onError={handleError}
      />
      <EditUserDialog
        key={dialog === "edit" ? selectedUser?.id : "closed"}
        user={dialog === "edit" ? selectedUser : null}
        onClose={closeSelectedDialog}
        onSuccess={handleSuccess}
        onError={handleError}
        currentUser={currentUser}
        roles={roles}
      />
      <ResetPasswordDialog
        user={dialog === "reset" ? selectedUser : null}
        onClose={closeSelectedDialog}
        onSuccess={handleSuccess}
        onError={handleError}
      />
      <UsersFilterDialog
        key={filterDialogOpen ? "filter-open" : "filter-closed"}
        open={filterDialogOpen}
        onClose={() => setFilterDialogOpen(false)}
        filters={filters}
      />

      <Notify {...notify} onOpenChange={(open) => { if (!open) closeNotify() }} />
    </Container>
  )
}
