import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import { Separator } from "@/components/ui/separator";
import { getServerSession } from "next-auth";
import { authOptions } from "@/auth";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Financial Insight Agent — Tài chính cá nhân, có số có nguồn",
  description:
    "Giáo trình tài chính cá nhân 10 module / 56 bài, 4 máy tính (thuế TNCN, trả nợ snowball–avalanche, lãi kép, ngân sách 50/30/20) và tra cứu RAG trên văn bản luật hiện hành — mọi con số kèm nguồn. Chỉ giáo dục, không khuyến nghị mua/bán.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  return (
    <html lang="vi" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body suppressHydrationWarning className="min-h-full flex flex-col bg-background">
        <Providers session={session}>
          <Header />
          <main className="flex-1 flex flex-col">{children}</main>
          <Toaster />
          <Separator />
          <footer className="py-4 text-center text-xs text-muted-foreground">
            Financial Insight Agent — Chỉ phục vụ giáo dục & thông tin, không phải lời khuyên tài chính.
          </footer>
        </Providers>
      </body>
    </html>
  );
}
