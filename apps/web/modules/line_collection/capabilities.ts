export function groupCapabilities(group: {
  joined: boolean; enabled: boolean; collecting?: boolean; processing?: boolean
}) {
  const bot = group.joined
    ? { label: "joined", variant: "success" } as const
    : { label: "left", variant: "muted" } as const
  const collection = !group.enabled
    ? { label: "disabled", variant: "muted" } as const
    : group.processing
      ? { label: "processing", variant: "warning" } as const
      : group.collecting
      ? { label: "collecting", variant: "success" } as const
      : { label: "waiting", variant: "warning" } as const
  return { canToggle: group.joined, nextEnabled: !group.enabled, bot, collection }
}
