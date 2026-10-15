import React from 'react';

// "Trâu Tí" — vector re-drawing (not a trace) of the user's mascot reference: chubby brown buffalo,
// cream horns, round blue glasses, a flower by the ear, a blue notebook. Single source for all poses.
export type TrauPose = 'idle' | 'happy' | 'think' | 'point' | 'wave' | 'celebrate' | 'shrug';
export const T = {
  fur: '#C06B3E', furDark: '#A4532F', belly: '#E3A26F', muzzle: '#EEB98E', horn: '#EFE3CF', hornTip: '#B9AA94',
  ink: '#4A2C1C', hoof: '#5A3A28', glass: '#2F6DB5', book: '#3C78C8', page: '#FFF7E8', petal: '#FFF1D6', flower: '#F2B632', inner: '#E79A8A',
};
export const TRAU_VIEWBOX = '-250 -240 520 450';
const OUT = 6;

const Limb: React.FC<{d: string}> = ({d}) => (
  <>
    <path d={d} fill="none" stroke={T.ink} strokeWidth={40} strokeLinecap="round" />
    <path d={d} fill="none" stroke={T.fur} strokeWidth={28} strokeLinecap="round" />
  </>
);
const Hoof: React.FC<{x: number; y: number}> = ({x, y}) => <circle cx={x} cy={y} r={18} fill={T.hoof} stroke={T.ink} strokeWidth={OUT} />;

const Book: React.FC<{x: number; y: number; rot?: number}> = ({x, y, rot = -8}) => (
  <g transform={`translate(${x} ${y}) rotate(${rot})`}>
    <rect x={-34} y={-44} width={68} height={88} rx={8} fill={T.book} stroke={T.ink} strokeWidth={OUT} />
    <rect x={-28} y={-38} width={8} height={76} rx={3} fill="#2D62AE" />
    <rect x={-12} y={-30} width={36} height={22} rx={4} fill={T.page} stroke={T.ink} strokeWidth={3} />
    <path d="M -8 -20 H 18 M -8 -14 H 10" stroke={T.ink} strokeWidth={3} strokeLinecap="round" />
  </g>
);

export const Trau: React.FC<{pose?: TrauPose; mouthOpen?: number}> = ({pose = 'idle', mouthOpen = 0}) => {
  const p: TrauPose = pose === 'celebrate' ? 'happy' : pose === 'shrug' ? 'idle' : pose;
  const open = Math.min(1, Math.max(0, mouthOpen));
  const talk = Math.min(1, open * 2.5); // 0 = pose mouth, 1 = fully talking
  const smile = p === 'wave' || p === 'point' || p === 'idle';
  const happyEyes = p === 'happy' || p === 'wave';
  const holdBook = p !== 'happy';
  return (
    <g>
      {/* tail */}
      <path d="M -74 110 Q -128 112 -132 62" fill="none" stroke={T.ink} strokeWidth={14} strokeLinecap="round" />
      <path d="M -74 110 Q -128 112 -132 62" fill="none" stroke={T.fur} strokeWidth={6} strokeLinecap="round" />
      <ellipse cx={-134} cy={54} rx={14} ry={20} fill={T.hoof} stroke={T.ink} strokeWidth={OUT} />

      {/* feet (sitting) */}
      <ellipse cx={-46} cy={146} rx={36} ry={20} fill={T.hoof} stroke={T.ink} strokeWidth={OUT} />
      <ellipse cx={46} cy={146} rx={36} ry={20} fill={T.hoof} stroke={T.ink} strokeWidth={OUT} />
      {/* body */}
      <ellipse cx={0} cy={72} rx={84} ry={78} fill={T.fur} stroke={T.ink} strokeWidth={OUT} />
      <ellipse cx={0} cy={86} rx={52} ry={54} fill={T.belly} />
      {p === 'happy' && <Book x={104} y={122} rot={12} />}

      {/* head */}
      {/* horns */}
      <path d="M -62 -128 C -108 -122 -146 -134 -152 -172 C -128 -152 -98 -156 -52 -148 Z" fill={T.horn} stroke={T.ink} strokeWidth={OUT} strokeLinejoin="round" />
      <path d="M -150 -170 C -146 -150 -136 -146 -128 -152 C -140 -156 -148 -164 -150 -170Z" fill={T.hornTip} />
      <path d="M 62 -128 C 108 -122 146 -134 152 -172 C 128 -152 98 -156 52 -148 Z" fill={T.horn} stroke={T.ink} strokeWidth={OUT} strokeLinejoin="round" />
      <path d="M 150 -170 C 146 -150 136 -146 128 -152 C 140 -156 148 -164 150 -170Z" fill={T.hornTip} />
      {/* ears */}
      <ellipse cx={-100} cy={-82} rx={30} ry={18} transform="rotate(-18 -100 -82)" fill={T.fur} stroke={T.ink} strokeWidth={OUT} />
      <ellipse cx={-100} cy={-82} rx={16} ry={9} transform="rotate(-18 -100 -82)" fill={T.inner} />
      <ellipse cx={100} cy={-82} rx={30} ry={18} transform="rotate(18 100 -82)" fill={T.fur} stroke={T.ink} strokeWidth={OUT} />
      <ellipse cx={100} cy={-82} rx={16} ry={9} transform="rotate(18 100 -82)" fill={T.inner} />
      <ellipse cx={0} cy={-62} rx={96} ry={84} fill={T.fur} stroke={T.ink} strokeWidth={OUT} />
      {/* forehead tuft */}
      <path d="M -14 -140 Q 0 -160 14 -140" fill="none" stroke={T.furDark} strokeWidth={8} strokeLinecap="round" />
      {/* flower */}
      <g transform="translate(92 -112)">
        {[0, 72, 144, 216, 288].map((a) => <circle key={a} cx={Math.cos((a * Math.PI) / 180) * 13} cy={Math.sin((a * Math.PI) / 180) * 13} r={10} fill={T.petal} stroke={T.ink} strokeWidth={3} />)}
        <circle r={7} fill={T.flower} stroke={T.ink} strokeWidth={3} />
      </g>
      {/* muzzle */}
      <ellipse cx={0} cy={-30} rx={52} ry={36} fill={T.muzzle} stroke={T.ink} strokeWidth={OUT - 1} />
      <ellipse cx={-18} cy={-34} rx={5} ry={7} fill={T.ink} /><ellipse cx={18} cy={-34} rx={5} ry={7} fill={T.ink} />
      {p === 'happy' && (<><path d={`M -22 -18 Q 0 ${14 + 22 * open} 22 -18 Z`} fill="#7A2E22" stroke={T.ink} strokeWidth={4} strokeLinejoin="round" /><path d="M -10 -4 Q 0 6 10 -4 Q 0 -1 -10 -4Z" fill="#E87F7A" /></>)}
      {smile && <path d={p === 'idle' ? 'M -18 -18 Q 0 -4 18 -18' : 'M -22 -18 Q 0 6 22 -18'} fill="none" stroke={T.ink} strokeWidth={6} strokeLinecap="round" opacity={1 - talk} />}
      {smile && talk > 0 && (<><ellipse cx={0} cy={-12} rx={16 + 6 * open} ry={4 + 16 * open} fill="#7A2E22" stroke={T.ink} strokeWidth={4} opacity={talk} />{open > 0.5 && <ellipse cx={0} cy={-4} rx={8} ry={5} fill="#E87F7A" opacity={talk} />}</>)}
      {p === 'think' && <path d="M -14 -16 Q -4 -22 4 -16 T 20 -16" fill="none" stroke={T.ink} strokeWidth={6} strokeLinecap="round" opacity={1 - talk} />}
      {p === 'think' && talk > 0 && <ellipse cx={3} cy={-16} rx={10 + 4 * open} ry={2 + 7 * open} fill="#7A2E22" stroke={T.ink} strokeWidth={4} opacity={talk} />}
      {/* glasses */}
      <circle cx={-40} cy={-80} r={30} fill="#fff" fillOpacity={0.35} stroke={T.glass} strokeWidth={8} />
      <circle cx={40} cy={-80} r={30} fill="#fff" fillOpacity={0.35} stroke={T.glass} strokeWidth={8} />
      <path d="M -10 -82 Q 0 -90 10 -82" fill="none" stroke={T.glass} strokeWidth={7} strokeLinecap="round" />
      <path d="M -70 -86 L -96 -92 M 70 -86 L 96 -92" stroke={T.glass} strokeWidth={7} strokeLinecap="round" />
      {happyEyes ? (<>
        <path d="M -54 -74 Q -40 -98 -26 -74" fill="none" stroke={T.ink} strokeWidth={8} strokeLinecap="round" />
        <path d="M 26 -74 Q 40 -98 54 -74" fill="none" stroke={T.ink} strokeWidth={8} strokeLinecap="round" /></>) : (<>
        <ellipse cx={p === 'think' ? -34 : -40} cy={p === 'think' ? -88 : -80} rx={15} ry={18} fill="#E8A21A" stroke={T.ink} strokeWidth={4} />
        <ellipse cx={p === 'think' ? 46 : 40} cy={p === 'think' ? -88 : -80} rx={15} ry={18} fill="#E8A21A" stroke={T.ink} strokeWidth={4} />
        <circle cx={p === 'think' ? -34 : -40} cy={p === 'think' ? -88 : -80} r={8} fill={T.ink} /><circle cx={p === 'think' ? 46 : 40} cy={p === 'think' ? -88 : -80} r={8} fill={T.ink} />
        <circle cx={p === 'think' ? -30 : -36} cy={p === 'think' ? -94 : -86} r={4} fill="#fff" /><circle cx={p === 'think' ? 50 : 44} cy={p === 'think' ? -94 : -86} r={4} fill="#fff" /></>)}
      {p === 'think' && <path d="M 18 -122 L 60 -130" stroke={T.ink} strokeWidth={7} strokeLinecap="round" />}

      {/* arms (front) */}
      {p === 'happy' && (<><Limb d="M -66 38 Q -124 22 -142 -34" /><Hoof x={-144} y={-44} /><Limb d="M 66 38 Q 124 22 142 -34" /><Hoof x={144} y={-44} /></>)}
      {holdBook && (<><Book x={-18} y={92} /><Limb d="M -66 42 Q -86 86 -40 98" /><Hoof x={-34} y={98} /></>)}
      {p === 'idle' && (<><Limb d="M 66 42 Q 98 70 96 112" /><Hoof x={96} y={118} /></>)}
      {p === 'think' && (<><Limb d="M 66 42 Q 112 60 96 6 Q 90 -8 54 -4" /><Hoof x={50} y={-4} /></>)}
      {p === 'point' && (<><Limb d="M 66 40 L 150 14" /><Hoof x={160} y={10} /><path d="M 176 4 L 204 -6" stroke={T.ink} strokeWidth={10} strokeLinecap="round" /></>)}
      {p === 'wave' && (<><Limb d="M 66 38 Q 126 20 142 -48" /><Hoof x={144} y={-58} />
        <path d="M 176 -98 Q 198 -82 194 -54" fill="none" stroke={T.ink} strokeWidth={7} strokeLinecap="round" />
        <path d="M 192 -116 Q 224 -92 218 -48" fill="none" stroke={T.ink} strokeWidth={7} strokeLinecap="round" /></>)}
      {p === 'think' && (<><circle cx={128} cy={-150} r={9} fill="#fff" stroke={T.ink} strokeWidth={5} /><circle cx={158} cy={-182} r={14} fill="#fff" stroke={T.ink} strokeWidth={5} />
        <ellipse cx={210} cy={-216} rx={34} ry={20} fill="#fff" stroke={T.ink} strokeWidth={5} /></>)}
    </g>
  );
};

export const TrauSvg: React.FC<{pose?: TrauPose; size?: number; mouthOpen?: number}> = ({pose = 'idle', size = 400, mouthOpen = 0}) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox={TRAU_VIEWBOX} width={size * (520 / 450)} height={size}>
    <Trau pose={pose} mouthOpen={mouthOpen} />
  </svg>
);
