export function groupCapabilities(group: { joined: boolean; enabled: boolean }) {
  return { canToggle: group.joined, nextEnabled: !group.enabled }
}
