import { ExchangePage, generateExchangeMetadata } from "@/modules/exchange_rates/public.server"

export const generateMetadata = generateExchangeMetadata

export default function Page() {
  return <ExchangePage />
}
