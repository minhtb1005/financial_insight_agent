"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getBackendUrl } from "@/lib/backend";

// Tab Danh gia: cham tay 1-5 canh RAGAS auto (RAGAS la eval offline, khong
// co per-trace). Admin-only (backend gate get_current_admin_user).

export type FeedbackItem = {
  id: number;
  score: number;
  comment: string;
  author: string;
  created_at: string;
};

export default function FeedbackTab({ traceId, token, initial }: { traceId: string; token?: string; initial?: FeedbackItem[] }) {
  const [items, setItems] = useState<FeedbackItem[]>(initial ?? []);
  const [score, setScore] = useState(5);
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState("");

  // Nap lai sau hanh dong tuong minh (submit) — khong fetch trong effect
  // (eslint react-hooks/set-state-in-effect), initial do server shell nap.
  async function reload() {
    try {
      const res = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(traceId)}/feedback`, {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) setItems((await res.json()).feedback ?? []);
    } catch {
      /* giu list cu */
    }
  }

  async function submit() {
    setMsg("");
    try {
      const res = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(traceId)}/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ score, comment }),
      });
      if (!res.ok) {
        setMsg(`Gửi thất bại: ${res.status}`);
        return;
      }
      setComment("");
      await reload();
      setMsg("Đã ghi nhận đánh giá.");
    } catch (e) {
      setMsg(`Lỗi: ${String(e)}`);
    }
  }

  return (
    <div className="space-y-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Chấm tay trace này (1–5)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2 text-sm">
          <select
            className="rounded border px-2 py-1"
            value={score}
            onChange={(e) => setScore(Number(e.target.value))}
            aria-label="Điểm"
          >
            {[1, 2, 3, 4, 5].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <input
            className="min-w-0 flex-1 rounded border px-2 py-1"
            placeholder="Nhận xét (tùy chọn, tối đa 2000 ký tự)"
            value={comment}
            maxLength={2000}
            onChange={(e) => setComment(e.target.value)}
          />
          <Button size="sm" onClick={submit}>Gửi</Button>
          {msg && <span className="text-xs text-muted-foreground">{msg}</span>}
        </CardContent>
      </Card>
      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-muted-foreground">Chưa có đánh giá nào.</p>}
        {items.map((f) => (
          <Card key={f.id}>
            <CardContent className="flex flex-wrap items-center gap-2 p-3 text-sm">
              <Badge>{f.score}/5</Badge>
              <span className="text-xs text-muted-foreground">{f.author}</span>
              <span className="text-xs text-muted-foreground">{f.created_at}</span>
              {f.comment && <p className="w-full">{f.comment}</p>}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
