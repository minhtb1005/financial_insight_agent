import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, FONT} from './theme';

// Chalkboard geometry (1080x1920 frame). Text lives inside this rect.
export const BOARD = {x: 70, y: 180, w: 940, h: 1030};
const PAD = 64;

// Wooden frame + tray + chalk lines. Lines appear sequentially (same 14-frame
// stagger as the old cards) and the active line gets a chalk underline wipe.
export const Board: React.FC<{parts: string[]; lineIdx: number; lineStarts: number[]}> = ({parts, lineIdx, lineStarts}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const n = parts.length;
  // Responsive so 6-line scenes (max in repo) still fit the 940px board.
  const fontSize = n <= 3 ? 58 : n === 4 ? 52 : 44;
  const gap = n >= 4 ? 16 : 24;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920}}>
      <svg width={1080} height={1920} style={{position: 'absolute', left: 0, top: 0}}>
        <rect x={54} y={164} width={972} height={1062} rx={16} fill={C.wood} stroke={C.woodDark} strokeWidth={6} />
        <rect x={66} y={176} width={948} height={1038} rx={8} fill={C.woodDark} />
        <rect x={BOARD.x} y={BOARD.y} width={BOARD.w} height={BOARD.h} rx={4} fill={C.board} />
        {/* faint chalk smudges */}
        <g opacity={0.05} fill="#fff">
          <ellipse cx={240} cy={520} rx={150} ry={60} transform="rotate(-8 240 520)" />
          <ellipse cx={720} cy={900} rx={180} ry={50} transform="rotate(6 720 900)" />
          <ellipse cx={520} cy={300} rx={120} ry={40} />
        </g>
        {/* chalk tray */}
        <rect x={84} y={1216} width={912} height={26} rx={6} fill={C.wood} stroke={C.woodDark} strokeWidth={4} />
        <rect x={128} y={1204} width={54} height={12} rx={6} fill="#F7F3E6" stroke="#CFC7B2" strokeWidth={2} />
        <rect x={196} y={1206} width={40} height={10} rx={5} fill="#F2C94C" stroke="#C9A227" strokeWidth={2} />
        {/* eraser */}
        <rect x={840} y={1196} width={90} height={20} rx={4} fill="#3E5C8A" stroke={C.woodDark} strokeWidth={3} />
        <rect x={846} y={1214} width={78} height={8} rx={3} fill="#E8E1CF" />
      </svg>
      <div style={{position: 'absolute', left: BOARD.x + PAD, top: BOARD.y, width: BOARD.w - 2 * PAD, height: BOARD.h,
        display: 'flex', flexDirection: 'column', justifyContent: 'center', gap, fontFamily: FONT, color: C.chalk}}>
        {parts.map((t, i) => {
          const reveal = spring({frame: frame - i * 14, fps, config: {damping: 14}});
          const active = i === lineIdx;
          const underline = active ? interpolate(frame - lineStarts[i], [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
          const underlineW = Math.min(100, ((t.length * fontSize * 0.56) / (BOARD.w - 2 * PAD)) * 100);
          return (
            <div key={i} style={{opacity: active ? 1 : 0.6, clipPath: `inset(-20px ${(1 - reveal) * 100}% -20px 0)`}}>
              <div style={{fontSize, fontWeight: 700, lineHeight: 1.3, textShadow: '0 0 8px rgba(255,255,255,0.18)'}}>
                {t.replace(/\[\[[^\]]*\]\]/g, '— (chờ số liệu) —')}
              </div>
              <div style={{height: 5, width: `${underline * underlineW}%`, background: C.chalk, borderRadius: 3, marginTop: 2}} />
            </div>
          );
        })}
      </div>
    </div>
  );
};
