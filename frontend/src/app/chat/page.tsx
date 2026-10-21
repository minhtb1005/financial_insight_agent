import { getServerSession } from "next-auth"
import { redirect } from "next/navigation"
import { authOptions } from "@/auth"
import { ChatContainer } from "@/components/chat/ChatContainer"

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ prompt?: string }> }) {
  const query = await searchParams
  const prompt = typeof query.prompt === "string" ? query.prompt.slice(0, 1000) : undefined
  const session = await getServerSession(authOptions)
  if (!session) {
    const destination = prompt ? `/chat?prompt=${encodeURIComponent(prompt)}` : "/chat"
    redirect(`/login?callbackUrl=${encodeURIComponent(destination)}`)
  }
  return <ChatContainer initialPrompt={prompt} />
}
