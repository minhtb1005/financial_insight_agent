"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  // Batch 2: comments per node (span_id optional, null = ca trace)
  const [comments, setComments] = useState<{ id: number; span_id: string | null; author: string; comment: string; created_at: string }[]>([]);
  const [cText, setCText] = useState("");
  const [cSpan, setCSpan] = useState("");

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
          <Select value={String(score)} onValueChange={(v) => setScore(Number(v))}>
            <SelectTrigger className="w-24" aria-label="Điểm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 4, 5].map((s) => (
                <SelectItem key={s} value={String(s)}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            className="min-w-0 flex-1"
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
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Comments per node</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex flex-wrap gap-2">
            <Input
              className="w-40 font-mono text-xs"
              placeholder="span_id (trống = cả trace)"
              value={cSpan}
              onChange={(e) => setCSpan(e.target.value)}
            />
            <Input
              className="min-w-0 flex-1"
              placeholder="Nhận xét node…"
              value={cText}
              maxLength={2000}
              onChange={(e) => setCText(e.target.value)}
            />
            <Button
              size="sm"
              onClick={async () => {
                if (!cText.trim()) return;
                const res = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(traceId)}/comments`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                  body: JSON.stringify({ comment: cText, span_id: cSpan.trim() || null }),
                });
                if (res.ok) {
                  setCText("");
                  const lr = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(traceId)}/comments`, {
                    cache: "no-store",
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                  });
                  if (lr.ok) setComments((await lr.json()).comments ?? []);
                }
              }}
            >
              Gửi comment
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={async () => {
                const lr = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(traceId)}/comments`, {
                  cache: "no-store",
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (lr.ok) setComments((await lr.json()).comments ?? []);
              }}
            >
              Tải comments
            </Button>
          </div>
          {comments.map((c) => (
            <div key={c.id} className="rounded border p-2 text-xs">
              <span className="font-mono">{c.span_id ?? "trace"}</span>{" "}
              <span className="text-muted-foreground">{c.author} · {c.created_at}</span>
              <p className="text-sm">{c.comment}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
