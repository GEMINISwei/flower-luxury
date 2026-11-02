export function groupCapabilities(group: { joined: boolean; enabled: boolean }) {
  const bot = group.joined
    ? { label: "joined", variant: "success" } as const
    : { label: "left", variant: "muted" } as const
  const collection = group.enabled
    ? { label: "collecting", variant: "success" } as const
    : { label: "disabled", variant: "muted" } as const
  return { canToggle: group.joined, nextEnabled: !group.enabled, bot, collection }
}
