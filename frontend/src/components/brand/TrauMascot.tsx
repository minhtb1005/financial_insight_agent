import { cn } from "@/lib/utils"

export type TrauMood = "welcome" | "thinking" | "teaching" | "celebrate" | "reading" | "careful"

/** Trâu Tí, drawn as a scalable vector so expressions stay crisp in every screen. */
export function TrauMascot({ mood = "welcome", className, compact = false }: {
  mood?: TrauMood
  className?: string
  compact?: boolean
}) {
  const happy = mood === "celebrate"
  const waving = mood === "welcome" || happy
  return (
    <svg viewBox={compact ? "45 20 230 180" : "0 0 340 360"} role="img" aria-label={`Trâu Tí — ${mood === "thinking" ? "đang suy nghĩ" : happy ? "chúc mừng bạn" : "bạn đồng hành tài chính"}`} className={cn("trau-mascot", className)} fill="none">
      {!compact && <>
        <ellipse cx="169" cy="336" rx="102" ry="13" fill="#152F2A" opacity=".09" />
        <path d="M100 281Q41 296 48 243" stroke="#54352B" strokeWidth="13" strokeLinecap="round" />
        <path d="M48 245q-19-9-7-28 21 1 7 28" fill="#54352B" />
        <ellipse cx="132" cy="320" rx="37" ry="19" fill="#54352B" />
        <ellipse cx="210" cy="320" rx="37" ry="19" fill="#54352B" />
        <path d="M106 182Q72 213 91 291Q102 325 171 322Q240 325 251 291Q270 214 232 182" fill="#C7865D" stroke="#54352B" strokeWidth="5" />
        <ellipse cx="171" cy="265" rx="55" ry="49" fill="#E8B98C" />
      </>}
      <path d="M102 66Q48 74 41 25Q67 50 111 43M237 66Q291 74 299 25Q272 50 229 43" fill="#F5E6CB" stroke="#54352B" strokeWidth="5" strokeLinejoin="round" />
      <ellipse cx="72" cy="108" rx="28" ry="19" transform="rotate(-24 72 108)" fill="#C7865D" stroke="#54352B" strokeWidth="5" />
      <ellipse cx="267" cy="108" rx="28" ry="19" transform="rotate(24 267 108)" fill="#C7865D" stroke="#54352B" strokeWidth="5" />
      <path d="M60 108l20-5M259 103l20 5" stroke="#E6A18C" strokeWidth="9" strokeLinecap="round" />
      <path d="M82 109Q77 44 170 42Q263 44 258 109L253 158Q248 204 170 210Q92 204 87 158Z" fill="#C7865D" stroke="#54352B" strokeWidth="5" />
      <path d="M144 47q8-19 24-9 14-14 30 8" fill="#A96543" />
      <ellipse cx="170" cy="164" rx="57" ry="38" fill="#F0C79E" />
      <ellipse cx="102" cy="151" rx="14" ry="8" fill="#D98F7A" opacity=".65" />
      <ellipse cx="239" cy="151" rx="14" ry="8" fill="#D98F7A" opacity=".65" />
      <g stroke="#315B75" strokeWidth="6">
        <circle cx="127" cy="118" r="30" fill="#FFFFFF" fillOpacity=".12" />
        <circle cx="213" cy="118" r="30" fill="#FFFFFF" fillOpacity=".12" />
        <path d="M157 117q13-9 26 0M97 112l-12-4M243 112l12-4" />
      </g>
      {happy ? <g stroke="#54352B" strokeWidth="5" strokeLinecap="round"><path d="M116 119q11-15 22 0M202 119q11-15 22 0" /></g> : <g fill="#352C28"><ellipse cx="129" cy="119" rx="5" ry="8" /><ellipse cx="211" cy="119" rx="5" ry="8" /><circle cx="131" cy="116" r="1.8" fill="white" /><circle cx="213" cy="116" r="1.8" fill="white" /></g>}
      <g fill="#81523F"><ellipse cx="152" cy="158" rx="5" ry="4" /><ellipse cx="188" cy="158" rx="5" ry="4" /></g>
      {mood === "careful" ? <path d="M157 183h26" stroke="#54352B" strokeWidth="4" strokeLinecap="round" /> : <path d={happy ? "M153 178Q170 207 187 178Z" : "M155 181q15 13 30 0"} stroke="#54352B" strokeWidth="4" strokeLinecap="round" fill={happy ? "#834638" : "none"} />}
      <g transform="translate(250 70)"><g fill="#FFFAEB" stroke="#C7A56D" strokeWidth="1.5"><ellipse cy="-10" rx="7" ry="10" /><ellipse cy="10" rx="7" ry="10" /><ellipse cx="-10" rx="10" ry="7" /><ellipse cx="10" rx="10" ry="7" /></g><circle r="6" fill="#E7B85B" /></g>
      {!compact && <>
        <g transform="rotate(-9 152 267)"><rect x="116" y="222" width="77" height="92" rx="9" fill="#315B75" stroke="#54352B" strokeWidth="4" /><path d="M127 224v86" stroke="#8DB6CB" strokeWidth="3" /><rect x="140" y="239" width="38" height="28" rx="3" fill="#F5E6CB" /><path d="M148 249h22m-22 8h15" stroke="#315B75" strokeWidth="3" strokeLinecap="round" /></g>
        <path d="M100 229q-25 39 28 49" stroke="#54352B" strokeWidth="28" strokeLinecap="round" /><path d="M100 229q-25 39 28 49" stroke="#C7865D" strokeWidth="19" strokeLinecap="round" /><ellipse cx="129" cy="278" rx="15" ry="13" fill="#54352B" />
        <g className={waving ? "trau-wave" : undefined}>
          <path d={waving ? "M241 229q44-9 43-52" : mood === "thinking" ? "M241 233q39-20-9-48" : mood === "teaching" ? "M241 229l61-14" : "M241 229q26 25 10 57"} stroke="#54352B" strokeWidth="29" strokeLinecap="round" />
          <path d={waving ? "M241 229q44-9 43-52" : mood === "thinking" ? "M241 233q39-20-9-48" : mood === "teaching" ? "M241 229l61-14" : "M241 229q26 25 10 57"} stroke="#C7865D" strokeWidth="20" strokeLinecap="round" />
          <circle cx={waving ? 284 : mood === "thinking" ? 232 : mood === "teaching" ? 302 : 251} cy={waving ? 177 : mood === "thinking" ? 185 : mood === "teaching" ? 215 : 286} r="15" fill="#54352B" />
        </g>
        {mood === "thinking" && <g fill="#F5E6CB" stroke="#315B75" strokeWidth="3"><circle cx="294" cy="85" r="5" /><circle cx="306" cy="66" r="9" /><path d="M297 40q-8-20 12-23 24-3 23 17 0 17-35 6" /></g>}
        {happy && <g stroke="#C68E34" strokeWidth="4" strokeLinecap="round"><path d="M35 154v16m-8-8h16M310 119v16m-8-8h16M280 302l8 9M51 302l-8 9" /></g>}
      </>}
    </svg>
  )
}
