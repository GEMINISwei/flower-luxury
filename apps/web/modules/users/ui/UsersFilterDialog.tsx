"use client"

import { FilterDialog, useStatusFilterOptions } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { usersMessages } from "../i18n"
import type { UserFilters } from "../types"

type UsersFilterDialogProps = {
  open: boolean
  onClose: () => void
  filters: UserFilters
}

/**
 * 使用者列表的篩選對話框。
 *
 * 字典與狀態選項在這裡自己取, 不從 `UsersView` 傳進來: 那些是這個對話框自己的顯示細節,
 * 讓它們往上冒只會讓列表元件多背幾個跟列表無關的變數。
 */
export default function UsersFilterDialog({
  open,
  onClose,
  filters,
}: UsersFilterDialogProps) {
  const t = useT(usersMessages)
  const statusFilterOptions = useStatusFilterOptions()

  return (
    <FilterDialog
      title={t("filterTitle")}
      open={open}
      onClose={onClose}
      fields={[
        { name: "name", label: t("colName"), type: "text" },
        {
          name: "is_disabled",
          label: t("colStatus"),
          type: "select",
          options: statusFilterOptions,
        },
      ]}
      initialValues={{
        name: filters.name,
        is_disabled: filters.isDisabled,
      }}
    />
  )
}
