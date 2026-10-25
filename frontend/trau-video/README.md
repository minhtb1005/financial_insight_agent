# trau-video — render personal-finance lesson videos from scene JSON

Pipeline: `public/lessons/<ID>_scenes.json` -> `scripts/tts.py` (per-scene Vietnamese voice + measured durations)
-> `scripts/render.mjs` (Remotion, 1080x1920) -> `out/<ID>.mp4`.

Setup:   npm install ; pip install edge-tts ; ffmpeg + ffprobe on PATH
Voice:   python3 scripts/tts.py M3L2            (needs internet; UNTESTED in build sandbox)
Render:  node scripts/render.mjs M3L2           (refuses while [[placeholders]] are open; --force = draft)
Preview: npm run studio

Tested in build sandbox: scene JSON -> Remotion stills (Vietnamese text OK). NOT tested: TTS, full-length render with audio.
Mascot: Trâu Tí (src/trau/Trau.tsx), poses happy|think|point|wave|idle. Export SVG/PNG: `node scripts/export-mascot.mjs`.

## Batch production and frontend

Current catalog: 66 lessons (56 personal finance, 10 market literacy).
The 82-item evaluation counts questions, not lessons. Run from this folder:

```powershell
node scripts/prepare-lessons.mjs
node scripts/batch-render.mjs --voice=vi-VN-NamMinhNeural
node scripts/check-production.mjs --complete
```

Nam Minh was selected on 22 October 2026 after Hoai My stopped returning audio.
The approved M1L1 video retains its original voice. Use `--ids=M1L2,M1L3` for a
subset. `VIDEO_PYTHON` selects Python with edge-tts; `CHROME` selects the browser.
FFmpeg and ffprobe must be on PATH. Only lesson narration is sent to TTS.

The batch resumes using text/voice and video source hashes. The last good video
remains published until its replacement passes video/audio/duration checks.
Failures are recorded in `out/batch-status.json`; other lessons continue.
Re-run the command to retry. `out/batch.lock` prevents overlapping runs; remove
a stale lock only after confirming its PID is no longer running. Keep the
computer awake while rendering; a stopped run can be resumed.

MP4s, posters, Vietnamese captions and `manifest.json` are published into
`frontend/public/lesson-videos/`. The lesson player uses native controls without
autoplay, refreshes pending entries every 30 seconds, and provides transcripts
and source links. Public lesson media is accessible without login, like `/learn`.
Watching does not mark a practice task complete. Caption timing matches the
renderer's chunk clock; it does not claim word-level speech alignment.

Generated media is excluded from Git. Deployment must include the complete
`public/lesson-videos` folder **before building/starting Next.js**, or serve this
path from static storage. Code alone does not contain the videos.
Use `check-production.mjs --complete` before reporting all videos complete.
Without `--complete`, it checks all scripts and ready media and reports progress.
