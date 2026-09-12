// Shared money formatting -- confirmed 2026-09-12: every financial figure
// displays with a "$" prefix and thousands separators, e.g. "$ 8,750.00",
// instead of a bare `n.toFixed(2)` ("8750.00"). Single-currency SGD per
// CLAUDE.md, so no currency-code suffix is needed alongside the "$".
// A non-breaking space ( ) sits between "$" and the number so a
// narrow stat tile can't line-wrap between them.
export function formatMoney(amount: number): string {
  const formatted = Math.abs(amount).toLocaleString('en-SG', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return amount < 0 ? `-$ ${formatted}` : `$ ${formatted}`
}
