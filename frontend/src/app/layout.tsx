import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import Link from "next/link";
import { getServerSession } from "next-auth";
import { authOptions } from "@/auth";

export const metadata: Metadata = {
  title: "Financial Insight — Hiểu tiền. Chủ động cuộc sống.",
  description:
    "Cùng Trâu Tí khám phá 56 bài học tài chính cá nhân bằng tiếng Việt. Học từ tình huống, thực hành ngân sách và tìm hiểu cùng trợ giảng AI.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  return (
    <html lang="vi" suppressHydrationWarning className="h-full antialiased">
      <body suppressHydrationWarning className="min-h-full flex flex-col bg-background">
        <Providers session={session}>
          <a href="#main-content" className="skip-link">Chuyển đến nội dung</a>
          <Header />
          <main id="main-content" className="flex-1 flex flex-col">{children}</main>
          <Toaster />
          <footer className="site-footer page-shell">
            <div><Link href="/" className="footer-brand">financial<span>insight</span></Link><p>Hiểu tiền hôm nay. Vững vàng ngày mai.</p></div>
            <nav aria-label="Liên kết cuối trang"><Link href="/learn">Lộ trình học</Link><Link href="/demo">Trải nghiệm demo</Link><Link href="/chat">Trợ giảng AI</Link></nav>
            <p className="footer-note">Nội dung phục vụ giáo dục và thông tin. Không thay thế tư vấn tài chính cá nhân.</p>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
