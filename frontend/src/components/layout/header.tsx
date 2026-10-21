"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import { useState } from "react"
import { ArrowUpRight, LogOut, Menu, X } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { TrauMascot } from "@/components/brand/TrauMascot"
import { cn } from "@/lib/utils"

export function Header() {
  const pathname = usePathname()
  const { data: session, status } = useSession()
  const [open, setOpen] = useState(false)
  const links = [
    { href: "/", label: "Khám phá" },
    { href: "/learn", label: "Lộ trình học" },
    { href: "/chat", label: "Trợ giảng AI" },
    { href: "/dashboard", label: "Thị trường" },
    ...(session?.user?.role === "admin" ? [{ href: "/traces", label: "Traces" }] : []),
  ]
  return (
    <header className="site-header">
      <div className="page-shell header-inner">
        <Link href="/" className="brand" aria-label="Financial Insight — trang chủ" onClick={() => setOpen(false)}><span className="brand-mark"><TrauMascot compact /></span><span>financial<span className="brand-light">insight</span><small>HIỂU TIỀN · HIỂU MÌNH</small></span></Link>
        <nav className="desktop-nav" aria-label="Điều hướng chính">{links.map((link) => <Link key={link.href} href={link.href} aria-current={pathname === link.href ? "page" : undefined} className={cn("nav-link", pathname === link.href && "active")}>{link.label}</Link>)}</nav>
        <div className="header-actions"><ThemeToggle />{status === "authenticated" ? <button className="logout-button" onClick={() => signOut({ callbackUrl: "/" })} aria-label="Đăng xuất" title="Đăng xuất"><LogOut size={18} /></button> : <Link href="/login" className="login-link">Đăng nhập</Link>}<Link href="/demo" className="header-cta">Thử ngay <ArrowUpRight size={16} /></Link><button className="menu-toggle" aria-label={open ? "Đóng menu" : "Mở menu"} aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen(!open)}>{open ? <X size={22} /> : <Menu size={22} />}</button></div>
      </div>
      {open && <nav className="mobile-nav" id="mobile-nav" aria-label="Điều hướng trên điện thoại">{links.map((link) => <Link key={link.href} href={link.href} onClick={() => setOpen(false)} aria-current={pathname === link.href ? "page" : undefined}>{link.label}<ArrowUpRight size={16} /></Link>)}{!session && <Link href="/login" onClick={() => setOpen(false)}>Đăng nhập <ArrowUpRight size={16} /></Link>}</nav>}
    </header>
  )
}
