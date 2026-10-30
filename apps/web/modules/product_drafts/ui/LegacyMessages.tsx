"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, ConfirmDialog, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { deleteLegacyMessage } from "../actions"
import { draftMessages } from "../i18n"
import type { MessageInfo } from "../types"
import MessageList from "./MessageList"

export default function LegacyMessages({ messages }: { messages: MessageInfo[] }) {
  const t = useT(draftMessages)
  const router = useRouter()
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function remove() {
    if (!selected) return
    submit(() => deleteLegacyMessage(selected), {
      onSuccess: () => { setSelected(null); router.refresh() }, onError: setError,
    })
  }
  return <>
    <p>{t("legacyHint")}</p>
    {!messages.length && <p>{t("noMessages")}</p>}
    {messages.map((message) => <div key={message.id}>
      <MessageList messages={[message]} />
      <Button variant="outlined" onClick={() => { setSelected(message.id); setError("") }}>
        {t("deleteLegacy")}</Button>
    </div>)}
    <ConfirmDialog title={t("deleteLegacy")} open={Boolean(selected)} isPending={isPending}
      confirmText={t("delete")} onClose={() => setSelected(null)} onConfirm={remove}>
      <p>{t("deleteLegacyHint")}</p>{error && <p role="alert">{error}</p>}
    </ConfirmDialog>
  </>
}
