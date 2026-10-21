/** Demo arithmetic only. The visitor chooses allocations; no prescribed budget ratio. */
export function calculateBudget(income: number, essentials: number, wants: number) {
  const safeIncome = Number.isFinite(income) ? Math.round(Math.max(0, income)) : 0
  const safeEssentials = Number.isFinite(essentials) ? Math.min(100, Math.max(0, essentials)) : 0
  const safeWants = Number.isFinite(wants) ? Math.min(100 - safeEssentials, Math.max(0, wants)) : 0
  const essentialAmount = Math.round(safeIncome * safeEssentials / 100)
  const wantsAmount = Math.min(safeIncome - essentialAmount, Math.round(safeIncome * safeWants / 100))
  return { essentials: essentialAmount, wants: wantsAmount, remaining: Math.max(0, safeIncome - essentialAmount - wantsAmount), remainingPercent: 100 - safeEssentials - safeWants }
}
