"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getBackendUrl } from "@/lib/backend";

// Y tuong hoc tu Langfuse TracesTable (MIT, ngoai ee/): sortable headers +
// column visibility + search + pagination co total. Tu implement theo stack
// Next 16 + shadcn Table, khong copy code Langfuse.

export type TraceRow = {
  trace_id: string;
  root_name?: string | null;
  status: string;
  started_at?: number | null;
  duration_ms?: number | null;
  num_spans: number;
  total_tokens: number;
};

type SortBy = "started_at" | "duration_ms" | "num_spans" | "total_tokens";

const ALL_COLS = ["trace_id", "root_name", "status", "duration", "spans", "tokens", "started"] as const;
type Col = (typeof ALL_COLS)[number];
const LS_KEY = "traces-cols-v1";

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      return true;
    } catch {
      return false;
    }
  }
}

// Date input YYYY-MM-DD -> epoch giay. Chot mui gio local (browser) trong comment:
// start-of-day / end-of-day theo gio local cua nguoi xem.
function dateToEpoch(date: string, endOfDay: boolean): number | undefined {
  if (!date) return undefined;
  const d = new Date(`${date}T${endOfDay ? "23:59:59.999" : "00:00:00"}`);
  const ms = d.getTime();
  return Number.isNaN(ms) ? undefined : ms / 1000;
}

export default function TracesTable({
  token,
  initialTraces,
  initialTotal,
}: {
  token?: string;
  initialTraces: TraceRow[];
  initialTotal: number;
}) {
  const [traces, setTraces] = useState<TraceRow[]>(initialTraces);
  const [total, setTotal] = useState(initialTotal);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [status, setStatus] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("started_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  const [copied, setCopied] = useState<string | null>(null);
  // Batch 2: row selection (không virtualized — chỉ code khi đo >10k rows;
  // hiện tại <1k nên div + pagination Batch 1 là đủ, YAGNI).
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [cols, setCols] = useState<Col[]>(() => {
    try {
      if (typeof window === "undefined") return [...ALL_COLS];
      const raw = window.localStorage.getItem(LS_KEY);
      if (!raw) return [...ALL_COLS];
      const parsed = JSON.parse(raw) as Col[];
      if (Array.isArray(parsed) && parsed.length > 0)
        return parsed.filter((c) => (ALL_COLS as readonly string[]).includes(c));
    } catch {
      /* giu default */
    }
    return [...ALL_COLS];
  });

  const toggleCol = (c: Col) => {
    setCols((prev) => {
      const next = prev.includes(c) ? prev.filter((x) => x !== c) : [...ALL_COLS].filter((x) => prev.includes(x) || x === c);
      try {
        localStorage.setItem(LS_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const load = async (args: {
    p: number;
    sb: SortBy;
    sd: "asc" | "desc";
    q: string;
    st: string;
    from: string;
    to: string;
  }) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(args.p * limit));
      params.set("sort_by", args.sb);
      params.set("sort_dir", args.sd);
      if (args.q.trim()) params.set("trace_id_search", args.q.trim());
      if (args.st) params.set("status", args.st);
      const from = dateToEpoch(args.from, false);
      const to = dateToEpoch(args.to, true);
      if (from !== undefined) params.set("from_ts", String(from));
      if (to !== undefined) params.set("to_ts", String(to));
      const res = await fetch(`${getBackendUrl()}/api/v1/traces?${params.toString()}`, {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setTraces(data.traces ?? []);
        setTotal(typeof data.total === "number" ? data.total : (data.count ?? 0));
      }
    } finally {
      setLoading(false);
    }
  };

  const applyFilter = () => {
    setPage(0);
    load({ p: 0, sb: sortBy, sd: sortDir, q: search, st: status, from: fromDate, to: toDate });
  };

  const gotoPage = (p: number) => {
    setPage(p);
    load({ p, sb: sortBy, sd: sortDir, q: search, st: status, from: fromDate, to: toDate });
  };

  const onSort = (c: SortBy) => {
    const sd = sortBy === c ? (sortDir === "asc" ? "desc" : "asc") : "desc";
    setSortBy(c);
    setSortDir(sd);
    setPage(0);
    load({ p: 0, sb: c, sd, q: search, st: status, from: fromDate, to: toDate });
  };

  const arrow = (c: SortBy) => (sortBy === c ? (sortDir === "asc" ? " ▲" : " ▼") : "");
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const show = (c: Col) => cols.includes(c);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Tìm trace_id…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && applyFilter()}
          className="w-52"
        />
        <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="w-40" aria-label="Từ ngày" />
        <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="w-40" aria-label="Đến ngày" />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          aria-label="Trạng thái"
        >
          <option value="">Tất cả status</option>
          <option value="ok">ok</option>
          <option value="error">error</option>
          <option value="running">running</option>
        </select>
        <Button onClick={applyFilter} disabled={loading}>
          {loading ? "Đang tải…" : "Lọc"}
        </Button>
        {selected.size > 0 && (
          <Button
            variant="destructive"
            onClick={async () => {
              if (!window.confirm(`Xóa ${selected.size} trace đã chọn? Không thể hoàn tác.`)) return;
              for (const id of selected) {
                await fetch(`${getBackendUrl()}/api/v1/traces/${id}`, {
                  method: "DELETE",
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
              }
              setSelected(new Set());
              load({ p: page, sb: sortBy, sd: sortDir, q: search, st: status, from: fromDate, to: toDate });
            }}
          >
            Xóa ({selected.size})
          </Button>
        )}
        <div className="flex flex-wrap items-center gap-1 text-xs">
          {ALL_COLS.map((c) => (
            <label key={c} className="flex items-center gap-1 rounded border px-1.5 py-0.5">
              <input type="checkbox" checked={cols.includes(c)} onChange={() => toggleCol(c)} />
              {c}
            </label>
          ))}
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">
              <input
                type="checkbox"
                aria-label="Chọn tất cả"
                checked={traces.length > 0 && traces.every((t) => selected.has(t.trace_id))}
                onChange={(e) => {
                  if (e.target.checked) setSelected(new Set(traces.map((t) => t.trace_id)));
                  else setSelected(new Set());
                }}
              />
            </TableHead>
            {show("trace_id") && <TableHead>trace_id</TableHead>}
            {show("root_name") && <TableHead>root</TableHead>}
            {show("status") && <TableHead>status</TableHead>}
            {show("duration") && (
              <TableHead className="cursor-pointer select-none" onClick={() => onSort("duration_ms")}>
                duration{arrow("duration_ms")}
              </TableHead>
            )}
            {show("spans") && (
              <TableHead className="cursor-pointer select-none" onClick={() => onSort("num_spans")}>
                spans{arrow("num_spans")}
              </TableHead>
            )}
            {show("tokens") && (
              <TableHead className="cursor-pointer select-none" onClick={() => onSort("total_tokens")}>
                tokens{arrow("total_tokens")}
              </TableHead>
            )}
            {show("started") && (
              <TableHead className="cursor-pointer select-none" onClick={() => onSort("started_at")}>
                started{arrow("started_at")}
              </TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {traces.map((t) => (
            <TableRow key={t.trace_id}>
              <TableCell>
                <input
                  type="checkbox"
                  aria-label={`Chọn ${t.trace_id}`}
                  checked={selected.has(t.trace_id)}
                  onChange={(e) => {
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (e.target.checked) next.add(t.trace_id);
                      else next.delete(t.trace_id);
                      return next;
                    });
                  }}
                />
              </TableCell>
              {show("trace_id") && (
                <TableCell className="font-mono text-xs">
                  <Link href={`/traces/${t.trace_id}`} className="underline">
                    {t.trace_id.slice(0, 12)}…
                  </Link>{" "}
                  <button
                    className="ml-1 rounded border px-1 text-[11px]"
                    title="Copy trace ID"
                    onClick={async () => {
                      const ok = await copyText(t.trace_id);
                      setCopied(ok ? t.trace_id : null);
                      setTimeout(() => setCopied(null), 1200);
                    }}
                  >
                    {copied === t.trace_id ? "✓" : "⧉"}
                  </button>
                </TableCell>
              )}
              {show("root_name") && <TableCell>{t.root_name ?? "—"}</TableCell>}
              {show("status") && (
                <TableCell>
                  <Badge variant={t.status === "ok" ? "default" : t.status === "error" ? "destructive" : "secondary"}>
                    {t.status}
                  </Badge>
                </TableCell>
              )}
              {show("duration") && (
                <TableCell>{t.duration_ms == null ? "—" : `${Math.round(t.duration_ms)} ms`}</TableCell>
              )}
              {show("spans") && <TableCell>{t.num_spans}</TableCell>}
              {show("tokens") && <TableCell>{t.total_tokens}</TableCell>}
              {show("started") && (
                <TableCell className="text-xs">
                  {t.started_at ? new Date(t.started_at * 1000).toLocaleString() : "—"}
                </TableCell>
              )}
            </TableRow>
          ))}
          {traces.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-sm text-muted-foreground">
                Chưa có trace nào.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div className="flex items-center gap-3 text-sm">
        <span className="text-muted-foreground">
          Tổng {total} · trang {page + 1}/{totalPages}
        </span>
        <Button variant="outline" size="sm" disabled={page === 0 || loading} onClick={() => gotoPage(Math.max(0, page - 1))}>
          ← Trước
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page + 1 >= totalPages || loading}
          onClick={() => gotoPage(page + 1)}
        >
          Sau →
        </Button>
      </div>
    </div>
  );
}
