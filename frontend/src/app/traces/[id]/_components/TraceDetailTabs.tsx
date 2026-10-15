"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SpanIODetail, { JsonBlock } from "./SpanIODetail";
import TraceWaterfall, { type Span } from "./TraceWaterfall";
import FeedbackTab, { type FeedbackItem } from "./FeedbackTab";

// 5 tabs: Tong quan / Chunks / Memory / Danh gia / Raw. RAGAS la eval offline, khong bao
// gio co per-trace nen gop thanh banner-note trong Tong quan (theo debate).

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function TraceDetailTabs({ trace, token, initialFeedback }: { trace: Record<string, any>; token?: string; initialFeedback?: FeedbackItem[] }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const spans = (trace.spans ?? []) as Record<string, any>[];
  const [selected, setSelected] = useState<Span | null>(null);
  const toolSpans = spans.filter((s) => s.kind === "tool" || s.kind === "llm");
  const root = spans.find((s) => s.parent_span_id == null) ?? spans[0];

  return (
    <Tabs defaultValue="overview">
      <TabsList>
        <TabsTrigger value="overview">Tổng quan</TabsTrigger>
        <TabsTrigger value="chunks">Chunks ({toolSpans.length})</TabsTrigger>
        <TabsTrigger value="memory">Memory</TabsTrigger>
        <TabsTrigger value="feedback">Đánh giá</TabsTrigger>
        <TabsTrigger value="raw">Raw</TabsTrigger>
      </TabsList>

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
