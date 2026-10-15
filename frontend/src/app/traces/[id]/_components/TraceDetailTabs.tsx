"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getBackendUrl } from "@/lib/backend";
import SpanIODetail, { JsonBlock } from "./SpanIODetail";
import TraceWaterfall, { type Span } from "./TraceWaterfall";
import FeedbackTab, { type FeedbackItem } from "./FeedbackTab";

// 5 tabs: Tong quan / Chunks / Memory / Danh gia / Raw. RAGAS la eval offline, khong bao
// gio co per-trace nen gop thanh banner-note trong Tong quan (theo debate).

// Y tuong DAG hoc tu Langfuse TraceGraph (MIT, ngoai ee/): SVG nhe noi bo,
// khong lib. Tu implement: x=depth*150, y=thu tu, noi parent->child.
function TraceDag({ spans }: { spans: Record<string, unknown>[] }) {
  const get = (s: Record<string, unknown>, k: string) => s[k] as string | null;
  const byId = new Map(spans.map((s) => [String(get(s, "span_id")), s]));
  const depth = new Map<string, number>();
  const visit = (id: string, chain: Set<string>): number => {
    if (depth.has(id)) return depth.get(id)!;
    if (chain.has(id)) return 0; // cycle-guard
    chain.add(id);
    const s = byId.get(id);
    const p = s ? get(s, "parent_span_id") : null;
    const d = p && byId.has(p) ? visit(p, chain) + 1 : 0;
    chain.delete(id);
    depth.set(id, d);
    return d;
  };
  spans.forEach((s) => visit(String(get(s, "span_id")), new Set()));
  const maxD = Math.max(0, ...depth.values());
  const H = Math.max(60, spans.length * 28 + 20);
  const W = (maxD + 1) * 150 + 20;
  const yOf = new Map(spans.map((s, i) => [String(get(s, "span_id")), 20 + i * 28]));
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="rounded border bg-background" role="img" aria-label="DAG spans">
      {spans.map((s) => {
        const id = String(get(s, "span_id"));
        const p = get(s, "parent_span_id");
        if (!p || !byId.has(p)) return null;
        const x1 = (depth.get(p) ?? 0) * 150 + 110;
        const x2 = (depth.get(id) ?? 0) * 150 + 10;
        const y1 = (yOf.get(p) ?? 20) + 8;
        const y2 = (yOf.get(id) ?? 20) + 8;
        return <line key={`${p}-${id}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeOpacity={0.4} />;
      })}
      {spans.map((s) => {
        const id = String(get(s, "span_id"));
        const x = (depth.get(id) ?? 0) * 150 + 10;
        const y = yOf.get(id) ?? 20;
        return (
          <g key={id}>
            <rect x={x} y={y} width={100} height={16} rx={4} className="fill-muted stroke-border" />
            <text x={x + 5} y={y + 12} fontSize={10} className="fill-foreground">
              {String(s.name ?? id).slice(0, 14)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// DELETE admin-only + confirm cuối (để cuối Batch 2 vì destructive).
function DeleteTraceButton({ traceId, token }: { traceId: string; token?: string }) {
  const router = useRouter();
  return (
    <Button
      variant="destructive"
      size="sm"
      onClick={async () => {
        if (!window.confirm(`Xóa trace ${traceId}? Không thể hoàn tác.`)) return;
        const res = await fetch(`${getBackendUrl()}/api/v1/traces/${encodeURIComponent(traceId)}`, {
          method: "DELETE",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) router.push("/traces");
        else window.alert(`Xóa thất bại: ${res.status}`);
      }}
    >
      Xóa trace
    </Button>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function TraceDetailTabs({ trace, token, initialFeedback }: { trace: Record<string, any>; token?: string; initialFeedback?: FeedbackItem[] }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const spans = (trace.spans ?? []) as Record<string, any>[];
  const [selected, setSelected] = useState<Span | null>(null);
  const toolSpans = spans.filter((s) => s.kind === "tool" || s.kind === "llm");
  const root = spans.find((s) => s.parent_span_id == null) ?? spans[0];

  return (
    <Tabs defaultValue="overview">
      <div className="mb-2 flex items-center justify-between">
        <TabsList>
          <TabsTrigger value="overview">Tổng quan</TabsTrigger>
          <TabsTrigger value="chunks">Chunks ({toolSpans.length})</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="feedback">Đánh giá</TabsTrigger>
          <TabsTrigger value="raw">Raw</TabsTrigger>
        </TabsList>
        <DeleteTraceButton traceId={String(trace.trace_id ?? "")} token={token} />
      </div>

      <TabsContent value="overview">
        <div className="space-y-3">
          <div className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
            RAGAS là eval offline theo batch, không có điểm per-trace — xem báo cáo eval khi cần chấm chất lượng.
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Summary</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2 text-sm">
              <Badge variant={trace.status === "ok" ? "default" : trace.status === "error" ? "destructive" : "secondary"}>
                {trace.status}
              </Badge>
              {trace.root_name && <span>{trace.root_name}</span>}
              {trace.duration_ms != null && <span>{Math.round(trace.duration_ms)} ms</span>}
              <span>{trace.num_spans ?? spans.length} spans</span>
              <span>{trace.total_tokens ?? 0} tokens</span>
            </CardContent>
          </Card>
          <TraceWaterfall
            spans={spans}
            selectedId={selected ? String(selected.span_id) : null}
            onSelect={(s) => setSelected(s)}
          />
          <details>
            <summary className="cursor-pointer text-sm text-muted-foreground">
              DAG spans ({spans.length} nodes)
            </summary>
            <TraceDag spans={spans} />
          </details>
          {selected && (
            <Card>
              <CardHeader>
                <CardTitle className="font-mono text-xs">span {String(selected.span_id)}</CardTitle>
              </CardHeader>
              <CardContent>
                <SpanIODetail span={selected} />
              </CardContent>
            </Card>
          )}
        </div>
      </TabsContent>

      <TabsContent value="chunks">
        <div className="space-y-2">
          {toolSpans.length === 0 && <p className="text-sm text-muted-foreground">Không có span tool/llm.</p>}
          {toolSpans.map((s) => (
            <SpanIODetail key={String(s.span_id)} span={s} />
          ))}
        </div>
      </TabsContent>

      <TabsContent value="memory">
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Attributes của root span (bộ nhớ / context agent truyền qua spans).</p>
          {root ? <JsonBlock value={root.attributes ?? null} /> : <p className="text-sm">Không có span.</p>}
        </div>
      </TabsContent>

      <TabsContent value="raw">
        <JsonBlock value={trace} />
      </TabsContent>

      <TabsContent value="feedback">
        <FeedbackTab traceId={String(trace.trace_id ?? "")} token={token} initial={initialFeedback ?? []} />
      </TabsContent>
    </Tabs>
  );
}
