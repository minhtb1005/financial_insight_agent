"use client"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { User, ChartNoAxesCombined } from "lucide-react"
import { TrauMascot } from "@/components/brand/TrauMascot"

export function MessageBubble({ role, content, isStreaming, dashboardBadge }: { role: "user" | "assistant"; content: string; isStreaming?: boolean; dashboardBadge?: string | null }) {
  const isUser = role === "user"
  // Simple citation highlight: [TICKER: ...]
  const highlighted = !isUser ? content.replace(/\[([^\]]+?:[^\]]+?)\]/g, " `$1` ") : content

  return (
    <div className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted">
          <TrauMascot compact mood={isStreaming ? "thinking" : "welcome"} />
        </div>
      )}
      <div className={cn("max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm", isUser ? "bg-primary text-primary-foreground rounded-br-sm" : "bg-muted rounded-bl-sm")}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-a:text-primary">
            {isStreaming && !content ? (
              <div className="space-y-2 not-prose" aria-label="Đang soạn câu trả lời">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-32" />
              </div>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{highlighted}</ReactMarkdown>
            )}
            {isStreaming && <span className="inline-block h-4 w-2 animate-pulse bg-primary ml-1 align-middle" />}
            {!isStreaming && dashboardBadge && (
              <div className="mt-2 flex flex-wrap gap-1">
                <Badge variant="secondary" className="text-xs"><ChartNoAxesCombined size={13} className="mr-1" />{dashboardBadge}</Badge>
              </div>
            )}
            {!isStreaming && !dashboardBadge && content && content.includes("`") && (
              <div className="mt-2 flex flex-wrap gap-1">
                <Badge variant="secondary" className="text-xs">Có trích dẫn</Badge>
              </div>
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  )
}
