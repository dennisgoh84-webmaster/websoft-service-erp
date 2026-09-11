/**
 * Shared helpers for the "Period from / Period to" calendar-month filter
 * convention (confirmed 2026-09-11: date-RANGE filters across the app use
 * a native month picker -- e.g. "2026-08" -- rather than picking an exact
 * day, since a from/to filter is almost always used to mean "that month
 * onward" / "up to that month", not a specific date).
 *
 * A single point-in-time date filter (e.g. Accounting Reports' "As at"
 * for a Trial Balance) is NOT part of this convention -- it stays a plain
 * `type="date"` input, since a period picker doesn't make sense for one
 * instant. Same for every ordinary form field that records one date on a
 * document (start date, due date, effective date, etc.) -- only FROM/TO
 * range filters use this.
 */

/** The first calendar day of `month` ("YYYY-MM"), as an ISO date string. */
export function monthStartISO(month: string): string {
  return month ? `${month}-01` : ''
}

/** The last calendar day of `month` ("YYYY-MM"), as an ISO date string. */
export function monthEndISO(month: string): string {
  if (!month) return ''
  const [year, mon] = month.split('-').map(Number)
  const lastDay = new Date(year, mon, 0).getDate() // day 0 of next month
  return `${month}-${String(lastDay).padStart(2, '0')}`
}

/** The "YYYY-MM" a `type="month"` input needs, from a stored ISO date. */
export function isoToMonth(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 7) : ''
}
