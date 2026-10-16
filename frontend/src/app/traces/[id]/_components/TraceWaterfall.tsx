"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// Waterfall collapsible tree that (y tuong hoc tu Langfuse TraceTree/Timeline,
// MIT ngoai ee/): dung cay that tu parent_span_id (DB that co 2898/3387 spans
// co parent, depth 3) thay vi indent tinh. Tu implement div-bars, khong
// virtualized (trace lon nhat ~32 spans).

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Span = Record<string, any>;

type Node = { span: Span; children: Node[] };

function buildTree(spans: Span[]): Node[] {
  const byId = new Map<string, Node>();
  for (const s of spans) byId.set(String(s.span_id), { span: s, children: [] });
  const roots: Node[] = [];
  for (const s of spans) {
    const node = byId.get(String(s.span_id))!;
    const pid = s.parent_span_id == null ? null : String(s.parent_span_id);
    if (pid && byId.has(pid) && pid !== String(s.span_id)) {
      byId.get(pid)!.children.push(node);
    } else {
      // orphan (parent missing) -> depth 0 nhu root
      roots.push(node);
    }
  }
  // sort children theo started_at de waterfall on dinh
  const sortRec = (n: Node, seen: Set<string>) => {
    if (seen.has(n.span.span_id)) return; // cycle-guard
    seen.add(n.span.span_id);
    n.children.sort((a, b) => (a.span.started_at ?? 0) - (b.span.started_at ?? 0));
    n.children.forEach((c) => sortRec(c, seen));
  };
  roots.sort((a, b) => (a.span.started_at ?? 0) - (b.span.started_at ?? 0));
  roots.forEach((r) => sortRec(r, new Set()));
  return roots;
}

function kindColor(kind?: string, status?: string): string {
  if (status === "error") return "bg-red-500";
  switch (kind) {
    case "llm":
      return "bg-blue-500";
    case "tool":
      return "bg-emerald-500";
    case "agent":
      return "bg-violet-500";
    default:
      return "bg-slate-400";
  }
}

function Row({
  node,
  depth,
  traceStart,
  traceDur,
  collapsed,
  toggle,
  selectedId,
  onSelect,
  visited,
}: {
  node: Node;
  depth: number;
  traceStart: number;
  traceDur: number;
  collapsed: Set<string>;
  toggle: (id: string) => void;
  selectedId: string | null;
  onSelect: (s: Span) => void;
  visited: Set<string>;
}) {
  const s = node.span;
  const id = String(s.span_id);
  if (visited.has(id)) return null; // cycle-guard luc render
  visited.add(id);
  const isCollapsed = collapsed.has(id);
  const start = typeof s.started_at === "number" ? s.started_at : traceStart;
  const dur = typeof s.duration_ms === "number" ? s.duration_ms / 1000 : 0;
  // trace duration 0/None (trace running 1 span) -> bar full-width
  const leftPct = traceDur > 0 ? Math.max(0, Math.min(100, ((start - traceStart) / traceDur) * 100)) : 0;
  const widthPct = traceDur > 0 ? Math.max(0, Math.min(100 - leftPct, (dur / traceDur) * 100)) : 100;

  return (
    <>
      <div
        className={`flex items-center gap-1 rounded px-1 py-0.5 text-xs hover:bg-accent/60 ${selectedId === id ? "bg-accent" : ""}`}
        style={{ paddingLeft: depth * 16 + 4 }}
      >
        {node.children.length > 0 ? (
          <Button variant="ghost" size="sm" className="h-4 w-4 shrink-0 p-0" onClick={() => toggle(id)} aria-label={isCollapsed ? "Mở" : "Thu gọn"}>
            {isCollapsed ? "▸" : "▾"}
          </Button>
        ) : (
          <span className="w-4 shrink-0 text-muted-foreground">·</span>
        )}
        <Button variant="ghost" className="min-w-0 flex-1 justify-start truncate px-1 py-0.5 text-left font-mono text-xs font-normal" onClick={() => onSelect(s)} title={id}>
          {s.name}
        </Button>
        <Badge variant="outline" className="shrink-0 text-[10px]">
          {s.kind ?? "?"}
        </Badge>
        <div className="relative h-3 w-40 shrink-0 overflow-hidden rounded bg-muted">
          <div
            className={`absolute top-0 h-full rounded ${kindColor(s.kind, s.status)}`}
            style={{ left: `${leftPct}%`, width: `${widthPct}%`, minWidth: 2 }}
          />
        </div>
        <span className="w-16 shrink-0 text-right text-muted-foreground">
          {s.duration_ms != null ? `${Math.round(s.duration_ms)}ms` : "—"}
        </span>
      </div>
      {!isCollapsed &&
        node.children.map((c) => (
          <Row
            key={String(c.span.span_id)}
            node={c}
            depth={depth + 1}
            traceStart={traceStart}
            traceDur={traceDur}
            collapsed={collapsed}
            toggle={toggle}
            selectedId={selectedId}
            onSelect={onSelect}
            visited={visited}
          />
        ))}
    </>
  );
}

export default function TraceWaterfall({
  spans,
  selectedId,
  onSelect,
}: {
  spans: Span[];
  selectedId: string | null;
  onSelect: (s: Span) => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const roots = useMemo(() => buildTree(spans), [spans]);
  const { traceStart, traceDur } = useMemo(() => {
    const starts = spans.map((s) => s.started_at).filter((x) => typeof x === "number") as number[];
    const ends = spans
      .map((s) => (typeof s.started_at === "number" && typeof s.duration_ms === "number" ? s.started_at + s.duration_ms / 1000 : null))
      .filter((x): x is number => x != null);
    if (starts.length === 0) return { traceStart: 0, traceDur: 0 };
    const t0 = Math.min(...starts);
    const t1 = ends.length > 0 ? Math.max(...ends) : t0;
    return { traceStart: t0, traceDur: Math.max(0, t1 - t0) };
  }, [spans]);

  const toggle = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (spans.length === 0) return <p className="text-sm text-muted-foreground">Không có span.</p>;

  return (
    <div className="rounded border p-2">
      {roots.map((r) => (
        <Row
          key={String(r.span.span_id)}
          node={r}
          depth={0}
          traceStart={traceStart}
          traceDur={traceDur}
          collapsed={collapsed}
          toggle={toggle}
          selectedId={selectedId}
          onSelect={onSelect}
          visited={new Set()}
        />
      ))}
    </div>
  );
}
