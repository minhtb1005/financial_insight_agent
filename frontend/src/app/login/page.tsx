"use client"
import { useState } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { z } from "zod"
import { AuthShell } from "@/components/layout/AuthShell"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowRight, LoaderCircle } from "lucide-react"

const loginSchema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(3, "Mật khẩu tối thiểu 3 ký tự"),
})

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("demo@finsight.vn")
  const [password, setPassword] = useState("demo123")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = loginSchema.safeParse({ email, password })
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Dữ liệu không hợp lệ")
      return
    }
    setLoading(true)
    setError("")
    try {
      const res = await signIn("credentials", { email, password, redirect: false })
      if (res?.ok) {
        const requested = new URLSearchParams(window.location.search).get("callbackUrl")
        const destination = new URL(requested || "/chat", window.location.origin)
        router.push(destination.origin === window.location.origin && !["/login", "/signup"].includes(destination.pathname) ? `${destination.pathname}${destination.search}${destination.hash}` : "/chat")
        router.refresh()
      } else {
        setError("Chưa thể đăng nhập. Kiểm tra email, mật khẩu và kết nối dịch vụ rồi thử lại.")
      }
    } catch {
      setError("Kết nối đang gián đoạn. Bạn có thể thử lại hoặc trải nghiệm demo trước.")
    } finally { setLoading(false) }
  }

  return (
    <AuthShell>
          <h2>Tiếp tục cùng Trâu Tí</h2>
          <p className="auth-description">Đăng nhập để trò chuyện với trợ giảng AI và tiếp tục những câu hỏi của bạn.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="ban@example.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mật khẩu</Label>
              <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••" />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>{loading ? <><LoaderCircle className="animate-spin" /> Đang đăng nhập…</> : <>Đăng nhập <ArrowRight /></>}</Button>
          </form>
          <div className="auth-bottom">
            Chưa có tài khoản? <Link href="/signup" className="text-primary hover:underline">Đăng ký</Link>
          </div>
          <div className="auth-demo-note">
            <p className="font-medium">Bạn đang khám phá sản phẩm?</p>
            <p>Tài khoản demo đã được điền sẵn. Hoặc <Link href="/demo" className="underline underline-offset-4">thử bài thực hành không cần đăng nhập</Link>.</p>
          </div>
    </AuthShell>
  )
}
