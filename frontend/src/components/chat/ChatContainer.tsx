"use client"
/* eslint-disable react-hooks/exhaustive-deps -- intentional mount-only effects for localStorage */
import { useEffect, useRef, useState } from "react"
import { useSession } from "next-auth/react"
import { useChatStore } from "@/store/chatStore"
import { useChatStream } from "@/hooks/useChatStream"
import { MessageBubble } from "./MessageBubble"
import { DashboardPanel } from "@/components/dashboard/DashboardPanel"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { Send, Square, Trash2, BookOpen, ArrowUpRight } from "lucide-react"
import { TrauMascot } from "@/components/brand/TrauMascot"
import Link from "next/link"
import { learningTracks, getLearningTrack, getLearningLesson, chatHref, type LearningContext } from "@/lib/curriculum"

const SUGGESTIONS = [
  "Mình mới đi làm, nên bắt đầu lập ngân sách thế nào?",
  "Làm sao phân biệt nhu cầu và mong muốn khi chi tiêu?",
  "Mình muốn tìm hiểu cách xây quỹ khẩn cấp.",
  "Giải thích hai phương pháp trả nợ snowball và avalanche.",
  "Những khoản phí ngân hàng nào mình nên kiểm tra?",
  "Vẽ ngân sách 50/30/20 cho thu nhập 12 triệu đồng và giải thích cách điều chỉnh.",
]

export function ChatContainer({ initialPrompt, learningContext }: { initialPrompt?: string; learningContext: LearningContext }) {
  const track = getLearningTrack(learningContext.track)
  const lesson = getLearningLesson(learningContext)
  const suggestions = lesson ? [lesson.question, ...(lesson.chartQuestion ? [lesson.chartQuestion] : [])] : learningContext.track === "market_literacy" ? track.modules.map((module) => module.lessons[0].question) : SUGGESTIONS
  const { messages, isStreaming, input, setInput, clear, chartSpecs, clearCharts } = useChatStore()
  const { send, stop } = useChatStream(learningContext)
  const { data: session } = useSession()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [mobileTab, setMobileTab] = useState("chat")
  useEffect(() => { if (initialPrompt) setInput(initialPrompt) }, [initialPrompt, setInput])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  // Scope browser history by user, track and lesson. Subscribe after hydration so
  // the previous scope's render cannot overwrite the newly selected history.
  const storageKey = `finsight-chat:v2:${session?.user?.email ?? "guest"}:${learningContext.track}:${learningContext.lesson_id ?? "general"}`
  useEffect(() => {
    stop()
    clearCharts()
    let restored = []
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey) ?? "[]")
      if (Array.isArray(parsed)) restored = parsed.filter((item) => item && ["user", "assistant"].includes(item.role) && typeof item.content === "string").slice(-50)
    } catch {}
    useChatStore.setState({ messages: restored, input: initialPrompt ?? "", isStreaming: false })
    const unsubscribe = useChatStore.subscribe((state, previous) => {
      if (state.messages !== previous.messages) {
        try { localStorage.setItem(storageKey, JSON.stringify(state.messages.slice(-100))) } catch {}
      }
    })
    return () => { unsubscribe(); stop() }
  }, [storageKey, stop, clearCharts])

  // messageId -> chart (để gắn chip "đang hiển thị ở Dashboard")
  const chartByOrigin = new Map(chartSpecs.map((c) => [c.originMessageId, c]))

  const handleSend = async () => {
    const q = input.trim()
    if (!q || isStreaming) return
    setInput("")
    await send(q)
  }

  const handleClear = async () => {
    stop()
    clear()
    clearCharts()
    try { localStorage.removeItem(storageKey) } catch {}
    try {
      const res = await fetch(`/api/memory?track=${learningContext.track}&lesson_id=${learningContext.lesson_id ?? ""}`, { method: "DELETE" })
      if (!res.ok) {
        console.warn("Failed to clear server memory:", res.status, await res.text().catch(() => ""))
      }
    } catch (err) {
      console.warn("Failed to clear server memory:", err)
    }
  }

  const chatPane = (
    <>
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-background to-muted/20">
        {messages.length === 0 ? (
          <div className="chat-welcome mx-auto max-w-3xl py-5">
            <div className="text-center mb-8">
              <TrauMascot mood="welcome" />
              <h2>Hôm nay, bạn muốn hiểu điều gì?</h2>
              <p className="chat-subtitle">{lesson ? `Đang học: ${lesson.title}. Cùng thử giải thích, làm bài tập và kiểm chứng điều mình hiểu.` : track.description}</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {suggestions.map((s) => (
                <button key={s} className="chat-suggestion" onClick={() => setInput(s)}>{s}<ArrowUpRight size={15} /></button>
              ))}
            </div>
            <p className="mt-6 text-center text-xs text-muted-foreground">Đọc giải thích, xem nguồn được cung cấp và hỏi tiếp khi cần làm rõ.</p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((m, idx) => (
              <MessageBubble
                key={m.id}
                role={m.role}
                content={m.content}
                isStreaming={isStreaming && idx === messages.length - 1 && m.role === "assistant"}
                dashboardBadge={
                  m.role === "assistant" && chartByOrigin.has(m.id)
                    ? `Đang hiển thị ở Dashboard (${chartByOrigin.get(m.id)?.spec.chart_type})`
                    : null
                }
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <Separator />
      <div className="bg-background p-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Kể mình nghe điều bạn muốn tìm hiểu…"
              aria-label="Câu hỏi cho trợ giảng AI"
              maxLength={1000}
              className="min-h-[48px] max-h-[120px] resize-none"
              rows={2}
              disabled={isStreaming}
            />
            <div className="flex flex-col gap-2">
              {isStreaming ? (
                <Button variant="destructive" size="icon" onClick={stop} aria-label="Dừng">
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={handleSend} disabled={!input.trim()} size="icon" aria-label="Gửi">
                  <Send className="h-4 w-4" />
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={handleClear} title="Xóa lịch sử" aria-label="Xóa lịch sử trò chuyện">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Enter để gửi · Shift + Enter để xuống dòng · {input.length}/1000 ký tự</p>
        </div>
      </div>
    </>
  )

  return (
    <div className="chat-workspace flex flex-col">
      <div className="flex flex-wrap items-center gap-3 border-b px-4 py-3 text-sm">
        <BookOpen size={15} /><Link className="underline" href={`/learn?track=${track.id}${lesson ? `&lesson=${lesson.id}` : ""}`}>{lesson ? lesson.title : "Lộ trình học"}</Link>
        <nav className="flex flex-wrap gap-2" aria-label="Lộ trình trò chuyện">{learningTracks.map((item) => <Link key={item.id} href={chatHref(item.id)} aria-current={item.id === track.id && !lesson ? "page" : undefined} className={`rounded-full border px-3 py-1 focus-visible:outline-2 ${item.id === track.id ? "border-primary bg-primary/10" : ""}`}>{item.title}{item.id === "market_literacy" ? " · Tự chọn" : ""}</Link>)}</nav>
        {lesson && <span className="text-xs text-muted-foreground">Ngữ cảnh bài {lesson.id} · Chọn tên lộ trình để hỏi rộng hơn</span>}
      </div>
      <div className="lg:hidden border-b px-4 pt-2">
        <Tabs value={mobileTab} onValueChange={setMobileTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="chart">
              Biểu đồ
              {chartSpecs.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {chartSpecs.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div className="flex flex-1 min-h-0 flex-col lg:flex-row">
        <div className={cn("flex-1 flex-col min-h-0", mobileTab === "chat" ? "flex" : "hidden lg:flex")}>
          {chatPane}
        </div>
        <aside
          className={cn(
            "border-t lg:border-t-0 lg:border-l lg:w-[520px] xl:w-[640px] lg:shrink-0 bg-background min-h-0",
            mobileTab === "chart" ? "flex flex-1 flex-col" : "hidden lg:flex lg:flex-col lg:flex-1"
          )}
          aria-label="Dashboard"
        >
          <DashboardPanel onRedraw={send} allowMarketRedraw={track.id === "market_literacy" && (!lesson || ["MK2L1", "MK2L2"].includes(lesson.id))} />
        </aside>
      </div>
    </div>
  )
}
