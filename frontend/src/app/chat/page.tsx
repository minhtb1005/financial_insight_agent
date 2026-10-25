import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { ChatContainer } from "@/components/chat/ChatContainer"
import { getLearningTrack, getLearningLesson, chatHref, type LearningContext } from "@/lib/curriculum"

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ prompt?: string; track?: string; lesson?: string }> }) {
  const query = await searchParams
  const prompt = typeof query.prompt === "string" ? query.prompt.slice(0, 1000) : undefined
  const context: LearningContext = { track: getLearningTrack(query.track).id, lesson_id: query.lesson }
  const lesson = getLearningLesson(context)
  context.lesson_id = lesson?.id
  const session = await getServerSession(authOptions)
  if (!session) {
    const destination = chatHref(context.track, lesson, prompt)
    redirect(`/login?callbackUrl=${encodeURIComponent(destination)}`)
  }
  return <ChatContainer key={`${context.track}:${context.lesson_id}`} initialPrompt={prompt} learningContext={context} />
}
