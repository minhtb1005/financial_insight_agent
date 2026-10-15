# trau-video — render personal-finance lesson videos from scene JSON

Pipeline: `public/lessons/<ID>_scenes.json` -> `scripts/tts.py` (per-scene Vietnamese voice + measured durations)
-> `scripts/render.mjs` (Remotion, 1080x1920) -> `out/<ID>.mp4`.

Setup:   npm install ; pip install edge-tts ; ffmpeg + ffprobe on PATH
Voice:   python3 scripts/tts.py M3L2            (needs internet; UNTESTED in build sandbox)
Render:  node scripts/render.mjs M3L2           (refuses while [[placeholders]] are open; --force = draft)
Preview: npm run studio

Tested in build sandbox: scene JSON -> Remotion stills (Vietnamese text OK). NOT tested: TTS, full-length render with audio.
Mascot: Trâu Tí (src/trau/Trau.tsx), poses happy|think|point|wave|idle. Export SVG/PNG: `node scripts/export-mascot.mjs`.
