import test from "node:test"
import assert from "node:assert/strict"
import { calculateBudget } from "../src/lib/budget.ts"

test("12 million demo allocates 55/25/20 and conserves income", () => {
  assert.deepEqual(calculateBudget(12_000_000, 55, 25), {
    essentials: 6_600_000, wants: 3_000_000, remaining: 2_400_000, remainingPercent: 20,
  })
})

test("allocations stay nonnegative and sum to income, including rounding boundaries", () => {
  for (const income of [0, 1, 3, 2_000_000, 12_345_679, 50_000_000]) {
    for (const essential of [-10, 0, 33, 50, 55, 100, 120]) {
      for (const wants of [-20, 0, 25, 50, 100, 130]) {
        const result = calculateBudget(income, essential, wants)
        assert.equal(result.essentials + result.wants + result.remaining, income)
        assert.ok(result.essentials >= 0 && result.wants >= 0 && result.remaining >= 0)
        assert.ok(result.remainingPercent >= 0 && result.remainingPercent <= 100)
      }
    }
  }
})

test("invalid and negative values cannot produce invalid balances", () => {
  for (const value of [NaN, Infinity, -Infinity, -1]) {
    const result = calculateBudget(value, value, value)
    assert.equal(result.essentials + result.wants + result.remaining, 0)
    assert.ok(Number.isFinite(result.remainingPercent))
  }
})
