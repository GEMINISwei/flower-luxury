import { GroupsPage, generateGroupsMetadata, type GroupsPageProps } from "@/modules/line_collection/public.server"

export const generateMetadata = generateGroupsMetadata
export default function Page(props: GroupsPageProps) {
  return <GroupsPage {...props} />
}
