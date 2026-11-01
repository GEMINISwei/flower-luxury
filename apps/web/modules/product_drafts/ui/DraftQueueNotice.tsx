"use client"
import Link from "next/link"
import { useT } from "@/shared/i18n/context"
import { draftMessages } from "../i18n"

export default function DraftQueueNotice({ created, completed }: {
  created?: string; completed?: boolean
}) {
  const t = useT(draftMessages)
  if (!created || !/^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(created)) return null
  return <p role="status">{t(completed ? "queueDone" : "createdNotice")}{" "}
    <Link href={`/products/${created}`}>{t("viewCreated")}</Link></p>
}
