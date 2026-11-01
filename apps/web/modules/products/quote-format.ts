export function formatQuoteNumbers(originalAmount: string, exchangeRate: string) {
  return {
    amount: Number(originalAmount).toLocaleString("en-US", { maximumFractionDigits: 0 }),
    rate: Number(exchangeRate).toLocaleString("en-US", {
      minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false,
    }),
  }
}
