import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import { groupMessages } from "../i18n"
import type { GroupInfo } from "../types"
import styles from "./groups.module.css"

export default function GroupBatchState({ group }: { group: GroupInfo }) {
  const t = useT(groupMessages)
  return <div>
    {group.enabled && <p>{t(group.collecting ? "collecting" : "waiting")}</p>}
    {group.batch_started_at && <p>{t("batchStart")}：
      {formatDateTime(group.batch_started_at, "Asia/Taipei")}</p>}
    {group.batch_ended_at && <p>{t("batchEnd")}：
      {formatDateTime(group.batch_ended_at, "Asia/Taipei")}</p>}
    {Boolean(group.issue_count) && <div className={styles.notice}>
      <p>{t("issueCount", { count: group.issue_count })}</p>
      <ul>{(group.issues ?? []).map((issue, index) => <li key={`${issue.occurred_at}-${index}`}>
        {formatDateTime(issue.occurred_at, "Asia/Taipei")} — {issue.reason}</li>)}</ul>
    </div>}
    {group.reply_failed && <p className={styles.notice}>{t("replyFailed")}</p>}
  </div>
}
