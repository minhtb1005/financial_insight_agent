import test from "node:test"
import assert from "node:assert/strict"
import { chartRows } from "../src/lib/chart-rows.ts"

test("nominal and real purchasing power remain separate series with aligned years", () => {
  const result = chartRows([
    { year: 1, symbol: "real", value: 102 },
    { year: 0, symbol: "nominal", value: 100 },
    { year: 1, symbol: "nominal", value: 106 },
    { year: 0, symbol: "real", value: 100 },
  ], "year", "value", ["nominal", "real"])
  assert.deepEqual(result.rows, [{ year: 0, series_0: 100, series_1: 100 }, { year: 1, series_0: 106, series_1: 102 }])
})

test("missing observations are not filled with zero or another symbol's price", () => {
  const result = chartRows([{ time: "2024-01-01", symbol: "A", close: 10 }, { time: "2024-01-02", symbol: "B", close: 20 }], "time", "close", ["A", "B"])
  assert.equal(result.rows[0].series_1, undefined)
  assert.equal(result.rows[1].series_0, undefined)
})

test("single series and budget categories retain their values", () => {
  const rows = [{ category: "needs", value: 6000000 }]
  assert.deepEqual(chartRows(rows, "category", "value", ["budget"]), { rows, keys: ["value"] })
})
