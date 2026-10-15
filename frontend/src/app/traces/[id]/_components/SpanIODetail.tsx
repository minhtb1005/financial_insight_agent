"use client";

import { Badge } from "@/components/ui/badge";

// Shared JSON block + truncation detect (y tuong hoc tu Langfuse truncation
// notice, MIT ngoai ee/). Gop chung thay vi file JsonViewer.tsx rieng.
// Tracer cat 2000 chars (TRACE_MAX_CONTENT_CHARS) kem suffix
// "...[truncated N chars]" — ban full khong luu nen chi hien Badge + note.

const TRUNC_MARKER = "...[truncated";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function containsTruncated(v: any, seen = new Set()): boolean {
  if (typeof v === "string") return v.includes(TRUNC_MARKER);
  if (Array.isArray(v)) return v.some((x) => containsTruncated(x, seen));
  if (v && typeof v === "object") {
    if (seen.has(v)) return false;
    seen.add(v);
    return Object.values(v).some((x) => containsTruncated(x, seen));
  }
  return false;
}

export function JsonBlock({ value }: { value: unknown }) {
  const truncated = containsTruncated(value);
  let text: string;
  try {
    text = typeof value === "string" ? value : JSON.stringify(value, null, 2) ?? "null";
  } catch {
    text = String(value);
  }
  return (
    <div className="space-y-1">
      {truncated && (
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="secondary">contains truncated</Badge>
          <span className="text-muted-foreground">
            Nội dung bị cắt ở 2000 ký tự lúc ghi (bản full không lưu).
          </span>
        </div>
      )}
      <pre className="overflow-auto rounded bg-muted p-3 text-xs">{text}</pre>
    </div>
  );
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function SpanIODetail({ span }: { span: Record<string, any> }) {
  return (
    <details className="rounded border p-2 text-sm">
      <summary className="cursor-pointer font-mono text-xs">
        {span.name}{" "}
        <span className="text-muted-foreground">
          [{span.kind ?? "?"}]{span.duration_ms != null ? ` ${Math.round(span.duration_ms)}ms` : ""}
        </span>{" "}
        <button
          className="ml-1 rounded border px-1 text-[11px]"
          title="Copy span ID"
          onClick={async (e) => {
            e.preventDefault();
            await copyText(String(span.span_id ?? ""));
          }}
        >
          ⧉ {String(span.span_id ?? "").slice(0, 8)}
        </button>
        {containsTruncated([span.inputs, span.outputs, span.attributes]) && (
          <Badge variant="secondary" className="ml-1">
            truncated
          </Badge>
        )}
      </summary>
      <div className="mt-2 space-y-3">
        <div>
          <div className="mb-1 text-xs font-semibold">inputs</div>
          <JsonBlock value={span.inputs ?? null} />
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold">outputs</div>
          <JsonBlock value={span.outputs ?? null} />
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold">attributes</div>
          <JsonBlock value={span.attributes ?? null} />
        </div>
        {span.error && (
          <div>
            <div className="mb-1 text-xs font-semibold">error</div>
            <JsonBlock value={span.error} />
          </div>
        )}
      </div>
    </details>
  );
}
