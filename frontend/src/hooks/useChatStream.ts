"use client"
import { useCallback, useEffect, useRef } from "react"
import { parseSSEChunk, type SSEEvent } from "@/lib/sse"
import { parseChartSpecEvent } from "@/lib/chart-spec"
import { useChatStore } from "@/store/chatStore"

import type { LearningContext } from "@/lib/curriculum"

export function useChatStream(learningContext: LearningContext) {
  const { addMessage, appendToLastAssistant, setIsStreaming } = useChatStore()
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => {
    const controller = abortRef.current
    abortRef.current = null
    controller?.abort()
  }, [])

  const send = useCallback(
    async (query: string) => {
      if (!query.trim() || abortRef.current) return
      const userId = crypto.randomUUID()
      addMessage({ id: userId, role: "user", content: query, createdAt: Date.now() })
      const assistantId = crypto.randomUUID()
      addMessage({ id: assistantId, role: "assistant", content: "", createdAt: Date.now() })
      setIsStreaming(true)

      const controller = new AbortController()
      abortRef.current = controller
      const append = (text: string) => {
        if (abortRef.current === controller && !controller.signal.aborted && useChatStore.getState().messages.at(-1)?.id === assistantId) appendToLastAssistant(text)
      }

      try {
        const { chartSpecs, activeChartId } = useChatStore.getState()
        const activeChartSpec = chartSpecs.find((c) => c.id === activeChartId)?.spec ?? null
        const res = await fetch("/api/ask-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, activeChartSpec, learning_context: learningContext }),
          signal: controller.signal,
        })

        if (!res.ok || !res.body) {
          const txt = await res.text()
          let detail = `Máy chủ trả về lỗi ${res.status}. Vui lòng thử lại.`
          try {
            const parsed = JSON.parse(txt) as { detail?: unknown }
            if (typeof parsed.detail === "string") detail = parsed.detail
          } catch {}
          append(`⚠️ ${detail}`)
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const { events, rest } = parseSSEChunk(buffer)
          buffer = rest
          for (const ev of events) handleEvent(ev, assistantId)
        }
        // flush remaining
        if (buffer.trim()) {
          const { events } = parseSSEChunk(buffer + "\n\n")
          for (const ev of events) handleEvent(ev, assistantId)
        }

        function handleEvent(ev: SSEEvent, originMessageId: string) {
          if (abortRef.current !== controller || controller.signal.aborted) return
          if (ev.event === "chunk") {
            // chunk data may be plain string or JSON escaped?
            let chunk = ev.data
            try {
              // if data is JSON stringified
              const parsed = JSON.parse(ev.data)
              if (typeof parsed === "string") chunk = parsed
            } catch {}
            append(chunk)
          } else if (ev.event === "chart_spec") {
            const spec = parseChartSpecEvent(ev.data)
            if (spec) {
              useChatStore.getState().setChartSpec(spec, originMessageId)
            } else {
              append("\n\n⚠️ Dashboard: nhận chart-spec không hợp lệ, bỏ qua.")
            }
          } else if (ev.event === "chart_error") {
            append(`\n\n⚠️ Dashboard: ${ev.data.slice(0, 300)}`)
          } else if (ev.event === "final") {
            try {
              const final = JSON.parse(ev.data)
              if (final.latency_ms) {
                // optional: could update message with latency
              }
            } catch {}
          } else if (ev.event === "error") {
            try {
              const error = JSON.parse(ev.data) as { detail?: unknown; request_id?: unknown }
              const detail = typeof error.detail === "string" ? error.detail : "Có lỗi khi xử lý câu hỏi."
              append(`\n\n⚠️ ${detail}`)
            } catch {
              append(`\n\n⚠️ ${ev.data.slice(0, 300)}`)
            }
          }
        }
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") {
          append(" (đã dừng)")
        } else {
          append(`\n\n⚠️ Lỗi kết nối: ${String(e).slice(0, 300)}`)
        }
      } finally {
        if (abortRef.current === controller) {
          setIsStreaming(false)
          abortRef.current = null
        }
      }
    },
    [addMessage, appendToLastAssistant, setIsStreaming, learningContext]
  )

  const stop = useCallback(() => {
    const controller = abortRef.current
    abortRef.current = null
    controller?.abort()
    setIsStreaming(false)
  }, [setIsStreaming])

  return { send, stop }
}
