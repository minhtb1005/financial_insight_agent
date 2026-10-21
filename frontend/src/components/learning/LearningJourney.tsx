"use client"

import { useMemo, useState, useSyncExternalStore } from "react"
import Link from "next/link"
import { useSession } from "next-auth/react"
import { ArrowRight, ArrowUpRight, BookOpen, Check, CheckCircle2, ChevronDown, ChevronRight, Search, Target } from "lucide-react"
import { curriculum, lessonCount, stages, type Lesson } from "@/lib/curriculum"
import { TrauMascot } from "@/components/brand/TrauMascot"

type SavedWork = Record<string, string>
const progressEvent = "finsight-learning-progress"
function subscribe(listener: () => void) {
  window.addEventListener("storage", listener)
  window.addEventListener(progressEvent, listener)
  return () => { window.removeEventListener("storage", listener); window.removeEventListener(progressEvent, listener) }
}
function readProgress(key: string) { try { return localStorage.getItem(key) ?? "{}" } catch { return "{}" } }
function parseProgress(raw: string): SavedWork {
  try {
    const value = JSON.parse(raw)
    if (!value || typeof value !== "object" || Array.isArray(value)) return {}
    const ids = new Set(curriculum.flatMap((module) => module.lessons.map((lesson) => lesson.id)))
    return Object.fromEntries(Object.entries(value).filter(([id, text]) => ids.has(id) && typeof text === "string")) as SavedWork
  } catch { return {} }
}
const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase()

function LessonActivity({ lesson, saved, onSave, onNext }: { lesson: Lesson; saved?: string; onSave: (id: string, note: string) => boolean; onNext: () => void }) {
  const [note, setNote] = useState(saved ?? "")
  const [error, setError] = useState("")
  return <div className="lesson-content" id={`content-${lesson.id}`}>
    <p className="lesson-question">“{lesson.question}”</p>
    <h3>Những điều mình sẽ cùng tìm hiểu</h3>
    <ul>{lesson.topics.map((topic) => <li key={topic}><Check size={14} />{topic}</li>)}</ul>
    <h3>Nhiệm vụ của bạn</h3><p className="mission-box">{lesson.activity}</p>
    <h3><label htmlFor={`note-${lesson.id}`}>Ghi lại kết quả hoặc điều bạn rút ra</label></h3>
    <textarea id={`note-${lesson.id}`} value={note} onChange={(event) => { setNote(event.target.value); setError("") }} maxLength={4000} placeholder="Mình đã thử… Điều mình nhận ra là… Bước tiếp theo của mình sẽ là…" aria-describedby={`hint-${lesson.id}`} />
    <p className="lesson-hint" id={`hint-${lesson.id}`}>Viết ít nhất 20 ký tự sau khi thực hành. Đây là ghi nhận của bạn, chưa được AI chấm điểm. Ghi chép được lưu trên trình duyệt này; không nhập thông tin tài khoản hoặc giấy tờ cá nhân.</p>
    <div className="lesson-actions"><button className="action-primary" disabled={note.trim().length < 20} onClick={() => { if (!onSave(lesson.id, note.trim())) setError("Trình duyệt chưa cho phép lưu. Hãy sao chép ghi chép của bạn trước khi rời trang.") }}><CheckCircle2 size={16} />{saved ? "Cập nhật ghi chép" : "Lưu & hoàn thành nhiệm vụ"}</button><Link className="action-text" href={`/chat?prompt=${encodeURIComponent(lesson.question)}`}>Hỏi trợ giảng AI <ArrowUpRight size={16} /></Link></div>
    {error && <p role="alert" className="lesson-hint text-destructive">{error}</p>}
    {saved && <div className="completion-note" role="status"><TrauMascot mood="celebrate" /><div><p><strong>Một bước nhỏ đã hoàn thành.</strong><br />Ghi chép của bạn đã được lưu. Mình tiếp tục nhé?</p><button className="action-text" onClick={onNext}>Khám phá bài tiếp theo <ArrowRight size={15} /></button></div></div>}
    {lesson.id === "M1L1" && <Link href="/demo" className="action-text mt-4">Thực hành với demo ngân sách <ArrowUpRight size={15} /></Link>}
  </div>
}

export function LearningJourney({ initialModule, initialLesson }: { initialModule?: string; initialLesson?: string }) {
  const { data: session } = useSession()
  const storageKey = `finsight-learning:v1:${session?.user?.email ?? "guest"}`
  const raw = useSyncExternalStore(subscribe, () => readProgress(storageKey), () => "{}")
  const saved = useMemo(() => parseProgress(raw), [raw])
  const initial = curriculum.find((module) => module.id === initialModule) ?? curriculum[0]
  const [selectedId, setSelectedId] = useState(initial.id)
  const [expanded, setExpanded] = useState(initial.lessons.find((lesson) => lesson.id === initialLesson)?.id ?? initial.lessons[0].id)
  const [stage, setStage] = useState("Tất cả")
  const [search, setSearch] = useState("")
  const selected = curriculum.find((module) => module.id === selectedId) ?? curriculum[0]
  const visibleModules = curriculum.filter((module) => stage === "Tất cả" || module.stage === stage)
  const lessons = search.trim() ? visibleModules.flatMap((module) => module.lessons).filter((lesson) => normalize(`${lesson.title} ${lesson.originalTitle} ${lesson.topics.join(" ")}`).includes(normalize(search))) : selected.lessons
  const completedCount = Object.keys(saved).length
  function selectModule(id: string) {
    const module = curriculum.find((item) => item.id === id)!
    setSelectedId(id); setExpanded(module.lessons[0].id); setSearch("")
  }
  function saveLesson(id: string, note: string) {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ ...parseProgress(readProgress(storageKey)), [id]: note }))
      window.dispatchEvent(new Event(progressEvent))
      return true
    } catch { return false }
  }
  function nextLesson(id: string) {
    const all = curriculum.flatMap((module) => module.lessons.map((lesson) => ({ ...lesson, moduleId: module.id })))
    const next = all[(all.findIndex((lesson) => lesson.id === id) + 1) % all.length]
    setStage("Tất cả"); setSearch(""); setSelectedId(next.moduleId); setExpanded(next.id)
  }
  return <div className="page-shell">
    <div className="page-intro"><p className="eyebrow"><BookOpen size={15} /> HÀNH TRÌNH HIỂU TIỀN</p><h1>Học điều mình cần.<br /><span className="serif-accent">Tiến bộ theo cách của mình.</span></h1><p>10 chủ đề, {lessonCount} bài học và những nhiệm vụ giúp bạn đưa kiến thức vào cuộc sống. Bắt đầu ở bất kỳ chặng nào bạn quan tâm.</p></div>
    <div className="learning-layout">
      <aside className="learning-sidebar workspace-card"><h2>Lộ trình của bạn</h2><div className="progress-caption"><span>{completedCount}/{lessonCount} nhiệm vụ hoàn thành</span><span>{Math.round(completedCount / lessonCount * 100)}%</span></div><div className="progress-track" role="progressbar" aria-label="Tiến độ học" aria-valuemin={0} aria-valuemax={lessonCount} aria-valuenow={completedCount}><span style={{ width: `${completedCount / lessonCount * 100}%` }} /></div><p className="storage-note">Tiến độ lưu trên trình duyệt này.</p><nav className="module-nav" aria-label="Chọn chủ đề">{visibleModules.map((module) => <button key={module.id} onClick={() => selectModule(module.id)} aria-pressed={selectedId === module.id}><span>{module.id.replace("M", "").padStart(2, "0")}</span><span>{module.title}</span></button>)}</nav></aside>
      <div>
        <div className="learning-tools" aria-label="Lọc chặng học">{stages.map((item) => <button key={item} className="filter-button" aria-pressed={stage === item} onClick={() => { setStage(item); const first = curriculum.find((module) => item === "Tất cả" || module.stage === item)!; selectModule(first.id) }}>{item}</button>)}</div>
        <label className="search-field"><Search size={17} /><span className="sr-only">Tìm bài học</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tìm điều bạn muốn hiểu: ngân sách, phí, gia đình…" type="search" /></label>
        {!search.trim() && <div className="module-detail"><span className="small-label">CHỦ ĐỀ {selected.id.replace("M", "").padStart(2, "0")} · {selected.lessons.length} BÀI HỌC</span><h2>{selected.title}</h2><p>{selected.description}</p><div className="module-outcome"><Target size={17} /><span>Bạn sẽ tạo ra: <strong>{selected.outcome.toLowerCase()}.</strong></span></div></div>}
        {search.trim() && <p className="storage-note" role="status">{lessons.length} bài học phù hợp</p>}
        <div className="lesson-list">{lessons.map((lesson) => <div key={lesson.id}><button className="lesson-button" aria-expanded={expanded === lesson.id} aria-controls={`content-${lesson.id}`} onClick={() => setExpanded(expanded === lesson.id ? "" : lesson.id)}><span>{saved[lesson.id] ? <CheckCircle2 size={19} className="text-primary" /> : lesson.id.split("L")[1].padStart(2, "0")}</span><span>{lesson.title}<small>{lesson.originalTitle}</small></span>{expanded === lesson.id ? <ChevronDown size={17} /> : <ChevronRight size={17} />}</button>{expanded === lesson.id && <LessonActivity key={`${lesson.id}:${storageKey}:${saved[lesson.id] === undefined ? "new" : "saved"}`} lesson={lesson} saved={saved[lesson.id]} onSave={saveLesson} onNext={() => nextLesson(lesson.id)} />}</div>)}</div>
        {!lessons.length && <div className="empty-results"><p>Chưa tìm thấy bài phù hợp. Thử một từ khóa ngắn hơn nhé.</p><button className="action-text" onClick={() => setSearch("")}>Xem lại các bài học <ArrowRight size={16} /></button></div>}
      </div>
    </div>
  </div>
}
