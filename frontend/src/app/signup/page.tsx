"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { signIn } from "next-auth/react"
import { z } from "zod"
import { AuthShell } from "@/components/layout/AuthShell"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowRight, LoaderCircle } from "lucide-react"

const signupSchema = z.object({
  name: z.string().min(2, "Tên tối thiểu 2 ký tự").max(100),
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(8, "Mật khẩu tối thiểu 8 ký tự").max(128),
  confirm: z.string(),
}).refine((d) => d.password === d.confirm, { message: "Mật khẩu xác nhận không khớp", path: ["confirm"] })

export default function SignupPage() {
  const router = useRouter()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = signupSchema.safeParse({ name, email, password, confirm })
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Dữ liệu không hợp lệ")
      return
    }
    setLoading(true)
    setError("")
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(data.detail || "Đăng ký thất bại")
        setLoading(false)
        return
      }
      // Auto login after register
      const loginRes = await signIn("credentials", { email, password, redirect: false })
      setLoading(false)
      if (loginRes?.ok) {
        router.push("/chat")
      } else {
        router.push("/login")
      }
    } catch {
      setError("Lỗi kết nối. Vui lòng thử lại.")
      setLoading(false)
    }
  }

  return (
    <AuthShell signup>
          <h2>Bắt đầu hành trình của bạn</h2>
          <p className="auth-description">Tạo tài khoản để học hỏi cùng trợ giảng AI. Mỗi tài khoản có cuộc hội thoại và bộ nhớ riêng.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Tên hiển thị</Label>
              <Input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="Tên bạn muốn được gọi" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" autoComplete="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="ban@example.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mật khẩu</Label>
              <Input id="password" autoComplete="new-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="Tối thiểu 8 ký tự" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Xác nhận mật khẩu</Label>
              <Input id="confirm" autoComplete="new-password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required placeholder="Nhập lại mật khẩu" />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>{loading ? <><LoaderCircle className="animate-spin" /> Đang tạo tài khoản…</> : <>Tạo tài khoản <ArrowRight /></>}</Button>
          </form>
          <div className="auth-bottom">
            Đã có tài khoản? <Link href="/login" className="text-primary hover:underline">Đăng nhập</Link>
          </div>
    </AuthShell>
  )
}
