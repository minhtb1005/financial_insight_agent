"use client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MOCK_SECTORS } from "@/lib/mock-data"
import { useSectors } from "@/hooks/useMarketData"

export function SectorView() {
  const { data, loading, error } = useSectors("1w")
  const rows = data?.sectors?.length ? data.sectors : MOCK_SECTORS
  const isLive = !!data?.sectors?.length

  if (loading && !data) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-56" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phân tích ngành</CardTitle>
        <CardDescription>
          Hiệu suất theo ngành{" "}
          {loading ? <Badge variant="secondary">Đang cập nhật…</Badge> : error ? <Badge variant="outline">Minh họa · Chưa kết nối</Badge> : isLive ? <Badge variant="default">Dữ liệu thị trường · 1 tuần</Badge> : <Badge variant="outline">Dữ liệu minh họa</Badge>}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ngành</TableHead>
              <TableHead className="text-right">% Thay đổi</TableHead>
              <TableHead className="text-right">Khối lượng</TableHead>
              <TableHead>Mã tiêu biểu</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s) => (
              <TableRow key={s.sector}>
                <TableCell className="font-medium">{s.sector}</TableCell>
                <TableCell className="text-right">
                  <Badge variant={s.changePct >= 0 ? "default" : "destructive"} className={s.changePct >= 0 ? "bg-green-600" : ""}>{s.changePct > 0 ? "+" : ""}{s.changePct.toFixed(1)}%</Badge>
                </TableCell>
                <TableCell className="text-right">{(s as unknown as { volume?: string }).volume ?? "—"}</TableCell>
                <TableCell><Badge variant="secondary">{s.topTicker}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!isLive && !loading && <p className="mt-2 text-xs text-muted-foreground">Dữ liệu minh họa để khám phá cách đọc bảng ngành. Chưa có dữ liệu thị trường để hiển thị.</p>}
      </CardContent>
    </Card>
  )
}
