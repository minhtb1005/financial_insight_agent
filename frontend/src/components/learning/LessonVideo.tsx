"use client"

import { useEffect, useState } from "react"

type VideoEntry = {
  status: "pending" | "ready"
  src?: string
  poster?: string
  captions?: string
  duration?: number
  transcript?: string[]
  sources?: { title: string; url: string }[]
}

export function LessonVideo({ lessonId, title }: { lessonId: string; title: string }) {
  const [entry, setEntry] = useState<VideoEntry | null>(null)
  const [failed, setFailed] = useState(false)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    async function load() {
      try {
        const response = await fetch("/lesson-videos/manifest.json", { cache: "no-store", signal: controller.signal })
        if (!response.ok) throw new Error("Video list unavailable")
        const manifest = await response.json()
        const video = manifest.lessons?.[lessonId] as VideoEntry | undefined
        if (!controller.signal.aborted) {
          setEntry(video ?? { status: "pending" })
          setFailed(false)
          if (video?.status !== "ready") timer = setTimeout(load, 30000)
        }
      } catch {
        if (!controller.signal.aborted) setFailed(true)
      }
    }
    load()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [lessonId, retry])

  return <section className="my-6 rounded-2xl border border-border bg-muted/30 p-4 sm:p-6" aria-label={`Video: ${title}`}>
    <div className="mb-4 flex items-center justify-between gap-3">
      <h3 className="!m-0">Học cùng Trâu Tí</h3>
      {entry?.duration && <span className="text-sm text-muted-foreground">{Math.floor(entry.duration / 60)}:{String(Math.round(entry.duration) % 60).padStart(2, "0")}</span>}
    </div>
    {failed ? <div role="status">
      <p>Chưa tải được video. Bạn vẫn có thể đọc và thực hành bài bên dưới.</p>
      <button className="action-text mt-2" onClick={() => { setFailed(false); setRetry(value => value + 1) }}>Thử tải lại video</button>
    </div> : entry?.status === "ready" && entry.src ? <>
      <video key={`${entry.src}:${retry}`} controls playsInline preload="none" poster={entry.poster}
        width={1080} height={1920} aria-label={title}
        className="mx-auto block aspect-[9/16] max-h-[70vh] w-full max-w-[360px] rounded-xl bg-slate-950 object-contain"
        onError={() => setFailed(true)}>
        <source src={entry.src} type="video/mp4" />
        {entry.captions && <track kind="captions" src={entry.captions} srcLang="vi" label="Tiếng Việt" />}
        Trình duyệt chưa hỗ trợ video. <a href={entry.src}>Mở file video</a>.
      </video>
      {!!entry.transcript?.length && <details className="mt-4 text-sm leading-7">
        <summary className="cursor-pointer font-medium focus-visible:outline-2 focus-visible:outline-offset-4">Đọc lời thoại</summary>
        <div className="mt-3 space-y-3">{entry.transcript.map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
      </details>}
      {!!entry.sources?.length && <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-medium focus-visible:outline-2 focus-visible:outline-offset-4">Nguồn tham khảo của video</summary>
        <ul className="mt-3 space-y-2">{entry.sources.map(source => <li key={source.url}><a className="underline underline-offset-4" href={source.url} target="_blank" rel="noreferrer">{source.title}</a></li>)}</ul>
      </details>}
    </> : <p role="status" className="text-sm text-muted-foreground">{entry ? "Video bài này đang được chuẩn bị. Bạn có thể bắt đầu với nội dung bên dưới." : "Đang tải video bài học…"}</p>}
  </section>
}
