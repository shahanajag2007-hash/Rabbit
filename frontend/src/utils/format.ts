const moneyFormatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

/** Same output as ui_theme.money(): ₹{value:,.0f} */
export function money(value: number | string | undefined | null): string {
  return `₹${moneyFormatter.format(Math.round(Number(value ?? 0)))}`
}

/** Render a float the way Python's str(float) does (e.g. 90.0 -> "90.0", 92.25 -> "92.25"). */
export function pyFloat(value: number | undefined | null): string {
  const n = Number(value ?? 0)
  return Number.isInteger(n) ? `${n}.0` : String(n)
}
