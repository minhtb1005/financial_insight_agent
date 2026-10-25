#!/usr/bin/env python3
"""Per-scene Vietnamese TTS -> public/audio/<ID>/<Sx>.mp3 + durations.json (measured with ffprobe).
Needs internet to speech.platform.bing.com (edge-tts, free, no key). UNTESTED in the build sandbox (network blocked there).
usage: python3 scripts/tts.py M3L2 [voice]   voices: vi-VN-HoaiMyNeural (female, default) | vi-VN-NamMinhNeural (male)
"""
import asyncio, hashlib, json, os, subprocess, sys
from pathlib import Path
import edge_tts

lid = sys.argv[1]
voice = sys.argv[2] if len(sys.argv) > 2 else "vi-VN-HoaiMyNeural"
lesson = json.load(open(f"public/lessons/{lid}_scenes.json", encoding="utf-8"))
out = Path(f"public/audio/{lid}"); out.mkdir(parents=True, exist_ok=True)
cache_path = out / "cache.json"
cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

def measure(f):
    seconds = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]).decode().strip())
    if seconds <= 0:
        raise ValueError(f"Invalid audio: {f}")
    return seconds

async def main():
    scenes = {}
    for s in lesson["scenes"]:
        f = out / f"{s['id']}.mp3"
        text = s["vo"]["text"]
        if "[[" in text:
            raise ValueError(f"Unresolved script: {lid}/{s['id']}")
        digest = hashlib.sha256(f"{voice}|-5%|{text}".encode()).hexdigest()
        if cache.get(s["id"]) == digest and f.exists() and f.stat().st_size > 0:
            scenes[s["id"]] = measure(f)
            continue
        temporary = f.with_suffix(".pending.mp3")
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, voice, rate="-5%").save(str(temporary))
                d = measure(temporary)
                os.replace(temporary, f)
                cache[s["id"]] = digest
                cache_path.write_text(json.dumps(cache), encoding="utf-8")
                break
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(2 ** (attempt + 1))
        scenes[s["id"]] = round(d, 2)
        print(lid, s["id"], d, flush=True)
    json.dump({"voice": voice, "scenes": scenes}, open(out / "durations.json", "w"), indent=2)
    print("total VO sec:", round(sum(scenes.values()), 1))
asyncio.run(main())
