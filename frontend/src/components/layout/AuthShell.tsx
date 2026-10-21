import type { ReactNode } from "react"
import { TrauMascot } from "@/components/brand/TrauMascot"

export function AuthShell({ children, signup = false }: { children: ReactNode; signup?: boolean }) {
  return <div className="page-shell auth-layout"><div className="auth-story"><p className="eyebrow">CÙNG TRÂU TÍ, TỪNG BƯỚC MỘT</p><h1>{signup ? "Một khởi đầu nhỏ." : "Chào bạn trở lại."}<br /><span className="serif-accent">Một hành trình của riêng bạn.</span></h1><p>Đặt câu hỏi, tìm hiểu điều chưa rõ và biến kiến thức tài chính thành những việc mình có thể làm mỗi ngày.</p><TrauMascot mood={signup ? "welcome" : "reading"} /></div><div className="workspace-card auth-form">{children}</div></div>
}
