import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import { StatusBadge } from "@/shared/ui"
import { groupCapabilities } from "../capabilities"
import { groupMessages } from "../i18n"
import type { GroupInfo } from "../types"
import styles from "./groups.module.css"

export default function GroupBatchState({ group }: { group: GroupInfo }) {
  const t = useT(groupMessages)
  const { collection } = groupCapabilities(group)
  return <div>
    <StatusBadge label={t(collection.label)} variant={collection.variant} />
    {Boolean(group.issue_count) && <div className={styles.notice}>
      <p>{t("issueCount", { count: group.issue_count })}</p>
      <ul>{(group.issues ?? []).map((issue, index) => <li key={`${issue.occurred_at}-${index}`}>
        {formatDateTime(issue.occurred_at, "Asia/Taipei")} — {issue.reason}</li>)}</ul>
    </div>}
    {group.reply_failed && <p className={styles.notice}>{t("replyFailed")}</p>}
  </div>
}
