import React from 'react';
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const BARS = [
  {label: 'Thiết yếu', pct: 50, value: '6tr', color: '#f2a65a'},
  {label: 'Linh hoạt', pct: 30, value: '3,6tr', color: '#7fb7be'},
  {label: 'Tương lai', pct: 20, value: '2,4tr', color: '#d98a8a'},
];

// Phase 0a technical slice: Blender clip + one 2D card + one VO track.
export const P0Slice: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const cardIn = spring({frame: Math.max(0, frame - 205), fps, config: {damping: 18, stiffness: 110}});
  const cardY = interpolate(cardIn, [0, 1], [-70, 0]);
  const cardOpacity = interpolate(frame, [205, 235], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#120d0a'}}>
      <OffthreadVideo
        src={staticFile('p0/blender-slice.mp4')}
        style={{width: '100%', height: '100%', objectFit: 'cover'}}
      />
      <Audio src={staticFile('audio/M1L1/S1.mp3')} volume={0.9} />

      <div
        style={{
          position: 'absolute',
          left: 80,
          right: 80,
          top: 110,
          padding: '34px 34px 30px',
          borderRadius: 28,
          backgroundColor: 'rgba(20, 14, 10, 0.86)',
          border: '1px solid rgba(242, 194, 122, 0.38)',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.35)',
          opacity: cardOpacity,
          transform: `translateY(${cardY}px)`,
          fontFamily: 'Arial, Helvetica, sans-serif',
        }}
      >
        <div style={{fontSize: 32, letterSpacing: 4, color: '#f2c27a', fontWeight: 700}}>
          BA CÁCH CHIA LƯƠNG
        </div>
        <div style={{fontSize: 21, color: '#e7d7c6', marginTop: 8}}>
          Ví dụ minh hoạ · 12 triệu/tháng
        </div>

        <div
          style={{
            display: 'flex',
            gap: 22,
            marginTop: 26,
            alignItems: 'flex-end',
            height: 215,
          }}
        >
          {BARS.map((bar, i) => {
            const grow = interpolate(frame, [225 + i * 9, 265 + i * 9], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div
                key={bar.label}
                style={{
                  flex: 1,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                }}
              >
                <div style={{fontSize: 25, fontWeight: 700, color: '#fff', marginBottom: 8}}>
                  {bar.value}
                </div>
                <div
                  style={{
                    width: '100%',
                    height: 155 * grow,
                    backgroundColor: bar.color,
                    borderRadius: 12,
                  }}
                />
                <div style={{fontSize: 19, color: '#f5e9dc', marginTop: 10}}>{bar.label}</div>
                <div style={{fontSize: 17, color: '#c9b6a4'}}>{bar.pct}%</div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
