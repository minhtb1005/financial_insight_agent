import Link from "next/link"
import { getServerSession } from "next-auth"
import { authOptions } from "@/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  MessageCircle,
  LayoutDashboard,
  BookOpen,
  Search,
  Quote,
  ShieldCheck,
  TrendingUp,
  ArrowRight,
  Check,
  Scale,
} from "lucide-react"

const MODULES = [
  { id: "M1", title: "Quản lý ngân sách & theo dõi chi tiêu", lessons: 7 },
  { id: "M2", title: "Quỹ khẩn cấp & thói quen tiết kiệm", lessons: 5 },
  { id: "M3", title: "Quản lý nợ & tín dụng", lessons: 7 },
  { id: "M4", title: "Ngân hàng & sản phẩm tài chính cơ bản", lessons: 5 },
  { id: "M5", title: "Bảo hiểm", lessons: 3 },
  { id: "M6", title: "Thuế TNCN & nghĩa vụ tài chính", lessons: 4 },
  { id: "M7", title: "Tâm lý học tiền bạc & hành vi tiêu dùng", lessons: 4 },
  { id: "M8", title: "Kế hoạch tài chính cá nhân dài hạn (không đầu tư)", lessons: 10 },
  { id: "M9", title: "An ninh tài chính số & phòng chống lừa đảo", lessons: 5 },
  { id: "M10", title: "Tài chính gia đình & quan hệ tiền bạc", lessons: 6 },
]

export default async function HomePage() {
  const session = await getServerSession(authOptions)

  return (
    <div className="flex flex-col">
      {/* Hero — 60/40, no kicker above H1, primary action under sub */}
      <section className="border-b">
        <div className="container mx-auto px-4 py-10 md:py-16 lg:py-20">
          <div className="grid gap-8 lg:grid-cols-[1.35fr_0.85fr] lg:gap-10 items-start">
            {/* Left */}
            <div className="min-w-0">
              <h1 className="text-[2.05rem] font-bold tracking-[-0.03em] leading-[1.08] sm:text-5xl lg:text-[3.25rem]">
                Tài chính cá nhân
                <span className="block text-foreground/90">
                  có số, có nguồn.
                </span>
                <span className="block text-muted-foreground text-[0.62em] font-semibold tracking-tight mt-1">
                  Học từ ngân sách đến thuế — mọi con số đều kiểm chứng được.
                </span>
              </h1>
              <p className="mt-4 max-w-[60ch] text-[15px] leading-7 text-muted-foreground sm:text-[17px]">
                Financial Insight Agent là trợ giảng tài chính cá nhân bằng tiếng Việt:
                giáo trình 10 module / 56 bài, 4 máy tính tài chính (thuế TNCN, trả nợ,
                lãi kép, ngân sách) và tra cứu RAG trên văn bản luật đang có hiệu lực.
                Chỉ giáo dục, không khuyến nghị mua/bán (TT 135/2025), không quản lý tiền hộ.
              </p>

              <div className="mt-7 flex flex-wrap gap-3">
                {session ? (
                  <>
                    <Link href="/chat">
                      <Button size="lg" className="shadow-[0_1px_0_rgba(0,0,0,0.08),0_8px_24px_rgba(67,56,202,0.18)]">
                        <MessageCircle className="mr-2 h-4 w-4" />
                        Bắt đầu trò chuyện
                        <ArrowRight className="ml-2 h-4 w-4 opacity-70" />
                      </Button>
                    </Link>
                    <Link href="/dashboard">
                      <Button size="lg" variant="outline">
                        <LayoutDashboard className="mr-2 h-4 w-4" />
                        Xem Dashboard minh họa
                      </Button>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link href="/login">
                      <Button size="lg" className="shadow-[0_1px_0_rgba(0,0,0,0.08),0_8px_24px_rgba(67,56,202,0.18)]">
                        Đăng nhập để bắt đầu
                        <ArrowRight className="ml-2 h-4 w-4 opacity-70" />
                      </Button>
                    </Link>
                    <Link href="/login">
                      <Button size="lg" variant="outline">
                        Dùng tài khoản demo
                      </Button>
                    </Link>
                  </>
                )}
              </div>

              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                demo@finsight.vn / demo123 — Chỉ phục vụ giáo dục &amp; thông tin.
                <span className="mx-1.5 opacity-40">·</span>
                Không khuyến nghị mua/bán hay sản phẩm cụ thể (TT 135/2025).
              </p>

              {/* Proof strip — inline, not cards */}
              <div className="mt-8 grid grid-cols-3 gap-0 overflow-hidden rounded-xl border bg-card sm:mt-10">
                <div className="px-3 py-4 text-center sm:px-4 sm:py-5">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Tài khoản chứng khoán cá nhân
                  </div>
                  <div className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight sm:text-xl">
                    13,0 tr
                  </div>
                  <div className="mt-1 text-[11px] leading-4 text-muted-foreground">
                    05/2026 · VSDC
                  </div>
                </div>
                <div className="border-l px-3 py-4 text-center sm:px-4 sm:py-5">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Chưa dùng tư vấn trả phí
                  </div>
                  <div className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight sm:text-xl">
                    95%
                  </div>
                  <div className="mt-1 text-[11px] leading-4 text-muted-foreground">
                    TVS 2026 · 1.000 người
                  </div>
                </div>
                <div className="border-l px-3 py-4 text-center sm:px-4 sm:py-5">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Đã dùng GenAI cho tài chính
                  </div>
                  <div className="mt-1 font-mono text-lg font-semibold tabular-nums tracking-tight sm:text-xl">
                    75%
                  </div>
                  <div className="mt-1 text-[11px] leading-4 text-muted-foreground">
                    Sun Life 2026
                  </div>
                </div>
              </div>

              <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
                Thêm: 59% tự đánh giá kiến thức ở mức cơ bản/thấp; 73% chưa có kế hoạch dài hạn (Sun Life/TVS 2026) · 24% hiểu biết tài chính cơ bản (S&P 2014, ghi rõ năm).
              </p>
            </div>

            {/* Right — curriculum panel as single card, offset shadow blur, no halo */}
            <div className="min-w-0 lg:sticky lg:top-20">
              <div className="overflow-hidden rounded-xl border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.06),0_12px_32px_rgba(0,0,0,0.08)]">
                <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-3">
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
                    10 module trong giáo trình
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-[11px] font-medium text-emerald-700 ring-1 ring-emerald-500/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    56 bài
                  </span>
                </div>

                {/* Module list — plain rows, no chart */}
                <ul className="divide-y">
                  {MODULES.map((m) => (
                    <li key={m.id} className="flex items-center gap-3 px-4 py-2">
                      <span className="w-7 shrink-0 font-mono text-[11px] font-semibold text-muted-foreground">
                        {m.id}
                      </span>
                      <span className="min-w-0 flex-1 text-[13px] leading-5">{m.title}</span>
                      <span className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
                        {m.lessons} bài
                      </span>
                    </li>
                  ))}
                </ul>

                <Separator />
                <div className="bg-muted/20 px-4 py-3">
                  <p className="text-[11px] leading-4 text-muted-foreground">
                    Giáo trình tài chính cá nhân v1.2 — 56 bài. Bắt đầu từ M1 (ngân sách),
                    đi dần tới M10 (tài chính gia đình).
                  </p>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Quote className="h-3.5 w-3.5" />
                Mọi số trong trả lời Chat đều kèm citation — bạn bấm là thấy nguồn.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works — 3 steps, distinct rhythm, not 3 equal icon-cards */}
      <section className="container mx-auto px-4 py-10 md:py-14">
        <div className="mx-auto max-w-5xl">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">Hỏi tiếng Việt, hiểu có căn cứ</h2>
            <p className="text-sm text-muted-foreground">Ba bước — không vòng vo</p>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {/* Step 01 — larger, with list */}
            <div className="rounded-xl border bg-card p-5 md:col-span-1">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  01
                </span>
                <span className="text-sm font-semibold">Đặt câu hỏi như bạn nghĩ</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                “50/30/20 là gì?”, “Nợ nào trả trước?”, “Thuế TNCN tính thế nào?”. Không cần đúng thuật ngữ.
              </p>
              <div className="mt-4 rounded-lg border bg-muted/40 p-3">
                <div className="flex items-center gap-2 text-xs font-medium">
                  <Search className="h-3.5 w-3.5 text-muted-foreground" />
                  Ví dụ câu hỏi
                </div>
                <ul className="mt-2 space-y-1.5 text-sm">
                  <li className="flex gap-2">
                    <span className="text-muted-foreground">·</span> 50/30/20 chia thu nhập thế nào?
                  </li>
                  <li className="flex gap-2">
                    <span className="text-muted-foreground">·</span> Nợ lãi cao hay nợ nhỏ trả trước?
                  </li>
                </ul>
              </div>
            </div>

            {/* Step 02 — centered emphasis */}
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-foreground text-xs font-semibold text-background">
                  02
                </span>
                <span className="text-sm font-semibold">Nhận giải thích + công thức</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Agent diễn giải bằng tiếng Việt sư phạm, kèm công thức và ví dụ số — máy tính chạy sẵn để bạn đối chiếu.
              </p>
              <div className="mt-4 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2.5 ring-1 ring-primary/10">
                <BookOpen className="h-4 w-4 text-primary" />
                <span className="text-sm">
                  FV = PV × (1 + r)<sup>n</sup>
                </span>
                <span className="ml-auto text-xs text-muted-foreground">lãi kép</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">Công thức toán cơ bản, kèm ví dụ từ máy tính lãi kép.</p>
            </div>

            {/* Step 03 — citation focus */}
            <div className="rounded-xl border bg-card p-5">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border bg-background text-xs font-semibold">
                  03
                </span>
                <span className="text-sm font-semibold">Kiểm chứng ngay trong câu trả lời</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Mọi khái niệm/số liệu đều có trích dẫn bấm được. Thiếu nguồn thì không khẳng định.
              </p>
              <div className="mt-4 rounded-lg border bg-card p-3">
                <div className="text-xs font-medium">Lương 30 triệu, 1 người phụ thuộc → thuế TNCN 415.000đ/tháng</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-2 py-1 text-[11px]">
                    <Quote className="h-3 w-3" /> Luật 109/2025
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-2 py-1 text-[11px]">
                    NĐ 253/2026
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sample Q&A — proves citation UX */}
      <section className="border-y bg-muted/30">
        <div className="container mx-auto px-4 py-10 md:py-12">
          <div className="mx-auto max-w-5xl">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4 text-primary" />
              <h2 className="text-base font-semibold tracking-tight">Trả lời mẫu — có trích dẫn</h2>
              <span className="ml-auto hidden text-xs text-muted-foreground sm:inline">
                Bấm citation để mở nguồn · Không phải khuyến nghị
              </span>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Câu hỏi</div>
                  <div className="mt-1 text-sm font-medium">“Lương 30 triệu, 1 người phụ thuộc — thuế TNCN bao nhiêu?”</div>
                  <div className="mt-4 rounded-lg border bg-muted/40 p-3 text-sm leading-6">
                    Giảm trừ bản thân 15,5 triệu + 6,2 triệu/người phụ thuộc → thu nhập tính thuế 8,3 triệu
                    → thuế TNCN <span className="font-semibold">415.000đ/tháng</span> (net 29.585.000đ), áp dụng kỳ 2026.
                    <span className="ml-1 inline-flex translate-y-0.5 gap-1">
                      <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/15">
                        [Luật 109/2025/QH15]
                      </span>
                      <span className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs font-medium ring-1 ring-border">
                        [NĐ 253/2026/NĐ-CP]
                      </span>
                    </span>
                    <div className="mt-2 rounded bg-amber-500/10 px-2.5 py-1.5 text-xs leading-5 text-amber-900 ring-1 ring-amber-500/20">
                      Đối chiếu văn bản hiện hành trước khi quyết toán.
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    Kèm giảm trừ, bậc thuế và ngày hiệu lực
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Câu hỏi</div>
                    <span className="inline-flex shrink-0 items-center rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 ring-1 ring-amber-500/20">
                      Số liệu minh họa
                    </span>
                  </div>
                  <div className="mt-1 text-sm font-medium">“3 khoản nợ nên trả theo thứ tự nào?”</div>
                  <div className="mt-4 rounded-lg border bg-muted/40 p-3 text-sm leading-6">
                    Snowball (trả khoản nhỏ trước) tổng lãi <span className="font-semibold">1.686.294đ</span>;
                    avalanche (lãi cao trước) <span className="font-semibold">1.633.573đ</span> — tiết kiệm
                    <span className="font-semibold"> 52.721đ</span>, cùng trả xong trong 10 tháng.
                    <p className="mt-2 text-[11px] leading-4 text-muted-foreground">
                      Giả định: 5 triệu @30%/năm + 20 triệu @12%/năm + 2 triệu @18%/năm, ngân sách trả nợ 3 triệu/tháng.
                    </p>
                    <div className="mt-2 rounded bg-amber-500/10 px-2.5 py-1.5 text-xs leading-5 text-amber-900 ring-1 ring-amber-500/20">
                      Đây là so sánh chiến lược, không phải lời khuyên.
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    Cùng một ngân sách, hai thứ tự trả khác nhau
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <Link href={session ? "/chat" : "/login"}>
                <Button size="sm">
                  <MessageCircle className="mr-2 h-3.5 w-3.5" />
                  Thử hỏi ngay
                </Button>
              </Link>
              <span className="inline-flex items-center text-xs text-muted-foreground">
                <ShieldCheck className="mr-1.5 h-3.5 w-3.5" />
                Guardrails + disclaimer tự động khi bạn hỏi theo hướng tư vấn cá nhân
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Trust strip — eval harness */}
      <section className="container mx-auto px-4 py-10">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-xl border bg-card p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-semibold">
                  <Scale className="h-4 w-4 text-primary" />
                  Độ tin cậy đo được — không nói miệng
                </h2>
                <p className="mt-1 max-w-[60ch] text-sm leading-6 text-muted-foreground">
                  Số đo từ lần chạy RAG eval gần nhất trên bộ 46 cases: trả lời có nguồn,
                  từ chối khi ngoài phạm vi, và tỷ lệ tìm đúng tài liệu.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <div className="text-right leading-5">
                  <div>evals/ · rag-20260910-064148</div>
                  <div className="text-muted-foreground">46 cases (38 in-scope + 8 out-of-scope)</div>
                </div>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border bg-muted/30 px-4 py-3">
                <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">citation</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">36/36</span>
                  <span className="text-xs text-muted-foreground">100%</span>
                </div>
                <div className="mt-1 text-xs leading-4 text-muted-foreground">Mọi khẳng định có số liệu đều kèm nguồn đúng</div>
              </div>
              <div className="rounded-lg border bg-muted/30 px-4 py-3">
                <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">từ chối out-of-scope</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">8/8</span>
                  <span className="text-xs text-muted-foreground">100%</span>
                </div>
                <div className="mt-1 text-xs leading-4 text-muted-foreground">Câu hỏi ngoài phạm vi giáo dục được từ chối</div>
              </div>
              <div className="rounded-lg border bg-muted/30 px-4 py-3">
                <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">retrieval hit-rate</div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">86,8%</span>
                </div>
                <div className="mt-1 text-xs leading-4 text-muted-foreground">Tài liệu đúng được tìm thấy trong top-k</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ — legal boundary */}
      <Separator />
      <section className="bg-muted/30">
        <div className="container mx-auto px-4 py-10 md:py-12">
          <div className="mx-auto max-w-5xl">
            <h2 className="text-base font-semibold tracking-tight">Ranh giới rõ ràng — để bạn an tâm</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border bg-card p-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <Scale className="h-4 w-4" />
                </div>
                <div className="mt-3 text-sm font-semibold">Có khuyến nghị mua/bán không?</div>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                  Không. Chỉ giáo dục theo TT 135/2025. Hỏi theo hướng tư vấn cá nhân sẽ được
                  chuyển thành kiến thức chung kèm disclaimer.
                </p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <TrendingUp className="h-4 w-4" />
                </div>
                <div className="mt-3 text-sm font-semibold">Số liệu lấy từ đâu?</div>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                  Giá và chỉ báo qua vnstock; quy định qua văn bản luật hiện hành — VBPL 24/2025,
                  Thông tư 96/2020, Thông tư 135/2025, Luật TNCN 109/2025, NĐ 253/2026,
                  BHXH 2026, CIC. Mỗi con số gắn nguồn bấm được.
                </p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <div className="mt-3 text-sm font-semibold">Tôi cần chuẩn bị gì?</div>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                  Không cần. Chỉ cần hỏi bằng tiếng Việt như bạn nghĩ. Tài khoản demo đã có sẵn để thử ngay.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Close CTA */}
      <section className="container mx-auto px-4 py-10">
        <div className="mx-auto max-w-3xl rounded-xl border bg-foreground px-6 py-8 text-center text-background sm:px-8">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">Hiểu tiền của mình, có số và có nguồn.</h2>
          <p className="mx-auto mt-2 max-w-[55ch] text-sm leading-6 text-background/70">
            Bắt đầu với một câu hỏi tiếng Việt. Mọi câu trả lời đều kèm nguồn — bạn kiểm chứng được ngay.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href={session ? "/chat" : "/login"}>
              <Button size="lg" variant="secondary" className="bg-background text-foreground hover:bg-background/90">
                <MessageCircle className="mr-2 h-4 w-4" />
                Bắt đầu trò chuyện
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="border-background/20 bg-transparent text-background hover:bg-background/10 hover:text-background">
                Xem Dashboard minh họa
              </Button>
            </Link>
          </div>
          <p className="mt-3 text-xs text-background/60">Chỉ giáo dục &amp; thông tin — không khuyến nghị mua/bán (TT 135/2025).</p>
        </div>
      </section>
    </div>
  )
}
