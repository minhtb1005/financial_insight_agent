#!/usr/bin/env python3
"""Per-scene Vietnamese TTS -> public/audio/<ID>/<Sx>.mp3 + durations.json (measured with ffprobe).
Needs internet to speech.platform.bing.com (edge-tts, free, no key). UNTESTED in the build sandbox (network blocked there).
usage: python3 scripts/tts.py M3L2 [voice]   voices: vi-VN-HoaiMyNeural (female, default) | vi-VN-NamMinhNeural (male)
"""
import asyncio, json, subprocess, sys
from pathlib import Path
import edge_tts

lid = sys.argv[1]
voice = sys.argv[2] if len(sys.argv) > 2 else "vi-VN-HoaiMyNeural"
lesson = json.load(open(f"public/lessons/{lid}_scenes.json", encoding="utf-8"))
out = Path(f"public/audio/{lid}"); out.mkdir(parents=True, exist_ok=True)

async def main():
    scenes = {}
    for s in lesson["scenes"]:
        f = out / f"{s['id']}.mp3"
        await edge_tts.Communicate(s["vo"]["text"], voice, rate="-5%").save(str(f))
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]).decode().strip())
        scenes[s["id"]] = round(d, 2)
        print(s["id"], d)
    json.dump({"voice": voice, "scenes": scenes}, open(out / "durations.json", "w"), indent=2)
    print("total VO sec:", round(sum(scenes.values()), 1))
asyncio.run(main())
