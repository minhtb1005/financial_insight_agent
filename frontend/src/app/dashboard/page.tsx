import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PriceTable } from "@/components/dashboard/PriceTable"
import { PriceChart, RSIChart } from "@/components/dashboard/PriceChart"
import { PortfolioCard } from "@/components/dashboard/PortfolioCard"
import { SectorView } from "@/components/dashboard/SectorView"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TrauMascot } from "@/components/brand/TrauMascot"
import { ChartNoAxesCombined } from "lucide-react"

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  if (!session) redirect("/login?callbackUrl=%2Fdashboard")

  return (
    <div className="page-shell dashboard-layout">
      <div className="dashboard-intro">
        <div className="page-intro"><p className="eyebrow"><ChartNoAxesCombined size={16} /> GÓC KHÁM PHÁ DỮ LIỆU</p><h1>Đọc con số.<br /><span className="serif-accent">Hiểu bức tranh.</span></h1><p>Quan sát thị trường qua bảng giá và biểu đồ. Mỗi khung hiển thị rõ khi đang dùng dữ liệu minh họa.</p></div>
        <TrauMascot mood="teaching" />
      </div>

      <Tabs defaultValue="price" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="price">Bảng giá</TabsTrigger>
          <TabsTrigger value="chart">Biểu đồ</TabsTrigger>
          <TabsTrigger value="portfolio">Danh mục</TabsTrigger>
          <TabsTrigger value="sector">Ngành</TabsTrigger>
        </TabsList>

        <TabsContent value="price" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Bảng giá</CardTitle>
              <CardDescription>Giá, khối lượng, SMA9, RSI14 — 6 mã tiêu biểu</CardDescription>
            </CardHeader>
            <CardContent className="p-0 sm:p-6">
              <PriceTable />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="chart" className="space-y-4">
          <PriceChart />
          <RSIChart />
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-4">
          <PortfolioCard />
        </TabsContent>

        <TabsContent value="sector" className="space-y-4">
          <SectorView />
        </TabsContent>
      </Tabs>
    </div>
  )
}
