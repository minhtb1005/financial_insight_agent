"use client"
import { useState } from "react"
import { suitabilityWarning, type ChartType } from "@/lib/chart-spec"
import { useChatStore } from "@/store/chatStore"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const CHART_LABELS: Record<ChartType, string> = {
  candlestick: "Nến",
  line: "Đường",
  bar: "Cột",
  area: "Vùng",
  pie: "Tròn",
  donut: "Vành",
  treemap: "Treemap",
  heatmap: "Heatmap",
  waterfall: "Waterfall",
  scatter: "Scatter",
}

/** Đổi loại biểu đồ local (instant, giữ data) + vẽ lại theo mã/khung mới (qua chat). */
export function DashboardControls({ chartId, onRedraw, allowMarketRedraw }: { chartId: string; onRedraw: (query: string) => Promise<void>; allowMarketRedraw: boolean }) {
  const chart = useChatStore((s) => s.chartSpecs.find((c) => c.id === chartId))
  const overrideChartType = useChatStore((s) => s.overrideChartType)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const [ticker, setTicker] = useState("")
  const [range, setRange] = useState("6 tháng")

  if (!chart) return null
  const warn = suitabilityWarning(chart.spec.chart_type, chart.spec.data.length, chart.spec.series.length)
  const categorical = chart.spec.x_field === "category"
  const hasOHLC = chart.spec.series.length === 1 && chart.spec.data.every((row) => ["open", "high", "low", "close"].every((field) => typeof row[field] === "number"))
  const allowedTypes: ChartType[] = categorical ? ["pie", "donut", "bar"] : ["line", "area", ...(hasOHLC ? ["candlestick" as const] : [])]

  const handleRedraw = () => {
    const q = `Vẽ biểu đồ ${CHART_LABELS[chart.spec.chart_type].toLowerCase()} ${ticker.trim()} ${range} và giải thích giới hạn của dữ liệu.`
    if (!isStreaming && ticker.trim() && allowMarketRedraw) void onRedraw(q)
  }

  return (
    <div className="space-y-2">
      <Separator />
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="chart-type-select" className="text-xs font-medium text-muted-foreground">
          Loại biểu đồ
        </label>
        <Select value={chart.spec.chart_type} onValueChange={(v) => overrideChartType(chartId, v as ChartType)}>
          <SelectTrigger id="chart-type-select" className="h-8 w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {allowedTypes.map((t) => (
              <SelectItem key={t} value={t}>
                {CHART_LABELS[t]}
                {t === chart.spec.chart_type ? " ✓" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {warn && (
          <Badge variant="secondary" className="text-xs">
            {warn}
          </Badge>
        )}
      </div>
      {allowMarketRedraw && <div className="flex flex-wrap items-center gap-2">
        <Input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="Mã, vd VNM"
          maxLength={8}
          className="h-8 w-28"
          aria-label="Mã chứng khoán"
        />
        <Select value={range} onValueChange={setRange}>
          <SelectTrigger className="h-8 w-32" aria-label="Khung thời gian">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {["1 tháng", "3 tháng", "6 tháng", "1 năm"].map((r) => (
              <SelectItem key={r} value={r}>
                {r}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" onClick={handleRedraw} disabled={isStreaming || !ticker.trim()}>
          Vẽ lại
        </Button>
      </div>}
    </div>
  )
}
