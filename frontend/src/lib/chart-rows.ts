type Row = Record<string, unknown>

/** Pivot long-form symbol rows. Missing observations stay missing, never become zero. */
export function chartRows(data: Row[], xField: string, yField: string, names: string[]) {
  const keys = names.map((_, index) => `series_${index}`)
  if (names.length < 2 || !data.some((row) => typeof row.symbol === "string")) {
    return { rows: data, keys: names.map(() => yField) }
  }
  const groups = new Map<unknown, Row>()
  for (const row of data) {
    const index = names.indexOf(String(row.symbol))
    if (index < 0) continue
    const point = groups.get(row[xField]) ?? { [xField]: row[xField] }
    point[keys[index]] = row[yField]
    groups.set(row[xField], point)
  }
  return { rows: [...groups.values()].sort((a, b) => typeof a[xField] === "number" && typeof b[xField] === "number"
    ? (a[xField] as number) - (b[xField] as number)
    : String(a[xField]).localeCompare(String(b[xField]))), keys }
}
