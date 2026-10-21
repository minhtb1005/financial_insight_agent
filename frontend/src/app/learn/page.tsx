import type { Metadata } from "next"
import { LearningJourney } from "@/components/learning/LearningJourney"

export const metadata: Metadata = { title: "Lộ trình học cùng Trâu Tí | Financial Insight" }

export default async function LearnPage({ searchParams }: { searchParams: Promise<{ module?: string; lesson?: string }> }) {
  const query = await searchParams
  return <LearningJourney key={`${query.module ?? "M1"}:${query.lesson ?? ""}`} initialModule={query.module} initialLesson={query.lesson} />
}
