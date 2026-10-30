#!/usr/bin/env python3
"""Render script.json as a vertical reel using free Openverse footage where available."""

import html
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
WIDTH, HEIGHT, FPS = 1080, 1920, 24
SCENE_SECONDS = 4
OPENVERSE = "https://api.openverse.org/v1/videos/"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
USER_AGENT = "JeffVideoForge/1.0 (free stock video renderer)"


def run(args):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT)


def font(size, bold=False):
    bundled = ROOT / "fonts" / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf")
    candidates = [bundled]
    candidates += [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def wrap_words(draw, text, face, max_width):
    lines, current = [], ""
    for word in text.split():
        test = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), test, font=face)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]


def make_card(text, keyword):
    """Pillow fallback retained for scenes without downloadable stock footage."""
    seed = sum(ord(ch) for ch in (keyword or text))
    colors = [(89, 34, 22), (121, 48, 25), (45, 59, 39), (154, 82, 34)]
    image = Image.new("RGB", (WIDTH, HEIGHT), colors[seed % len(colors)])
    draw = ImageDraw.Draw(image, "RGBA")
    for i in range(12):
        x = (seed * (i + 7) * 37) % WIDTH
        y = (seed * (i + 11) * 53) % HEIGHT
        radius = 180 + (seed + 47 * i) % 300
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(245, 157, 66, 16))
    return image


def make_caption_overlay(text):
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    face = font(58, True)
    lines = wrap_words(draw, text, face, WIDTH - 200)[:3]
    line_height = 82
    panel_height = len(lines) * line_height + 70
    top = 1320
    draw.rounded_rectangle((62, top, WIDTH-62, top+panel_height), radius=34,
                           fill=(0, 0, 0, 178), outline=(255, 255, 255, 70), width=2)
    y = top + 30
    for line in lines:
        draw.text((105, y), line, font=face, fill="white", stroke_width=3, stroke_fill=(0, 0, 0, 255))
        y += line_height
    return overlay


def simple_keyword(keyword):
    words = re.findall(r"[a-z0-9]+", keyword.lower())
    stop = {"the", "and", "with", "from", "into", "over", "under", "while", "scene", "clip", "video", "a", "an", "of", "in", "on", "to", "for"}
    useful = [word for word in words if word not in stop]
    return " ".join(useful[:3]) or "people"


def openverse_results(query):
    url = OPENVERSE + "?" + urllib.parse.urlencode({"q": query, "page_size": 8})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read(2_000_000).decode("utf-8"))
    return payload.get("results", [])


def commons_results(query):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:video {query}", "gsrnamespace": 6, "gsrlimit": 8,
        "prop": "imageinfo", "iiprop": "url|extmetadata",
    }
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read(2_000_000).decode("utf-8"))
    results = []
    for page in payload.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata", {})
        def meta(name, default=""):
            value = metadata.get(name, {})
            return html.unescape(re.sub(r"<[^>]+>", "", value.get("value", default))) if isinstance(value, dict) else default
        results.append({
            "title": page.get("title", "Untitled video"),
            "url": info.get("url", ""),
            "source_url": info.get("descriptionurl", ""),
            "creator": meta("Artist", "Unknown creator"),
            "license": meta("LicenseShortName", "Unknown license"),
            "license_version": "",
            "license_url": meta("LicenseUrl", ""),
        })
    return results


def download_candidate(result, scene_index, work, query, provider):
    source = result.get("url") or result.get("download_url")
    if not source:
        raise ValueError("result has no video URL")
    request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise ValueError("clip exceeds 100 MB download limit")
        if content_type and not (content_type.startswith("video/") or "octet-stream" in content_type):
            raise ValueError(f"not a video content type: {content_type}")
        body = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(body) > MAX_DOWNLOAD_BYTES:
        raise ValueError("clip exceeds 100 MB download limit")
    path = work / f"source_{scene_index:03d}.bin"
    path.write_bytes(body)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], cwd=ROOT, capture_output=True, text=True, timeout=12)
    if probe.returncode or "video" not in probe.stdout:
        raise ValueError("download is not a readable video")
    return path, {
        "title": result.get("title", "Untitled video"),
        "creator": result.get("creator", "Unknown creator"),
        "license": result.get("license", "Unknown license"),
        "license_version": result.get("license_version", ""),
        "license_url": result.get("license_url", ""),
        "source_url": result.get("foreign_landing_url") or result.get("source_url") or source,
        "query": query,
        "provider": provider,
    }


def download_openverse(keyword, scene_index, work):
    """Try Openverse query variants, then Wikimedia Commons, else report card fallback."""
    queries = [keyword, simple_keyword(keyword)]
    tried = set()
    failures = []
    for query in queries:
        if not query or query.lower() in tried:
            continue
        tried.add(query.lower())
        try:
            results = openverse_results(query)
        except urllib.error.HTTPError as exc:
            failures.append(f"Openverse {query!r}: HTTP {exc.code}")
            print(f"Scene {scene_index}: Openverse returned HTTP {exc.code} for {query!r}")
            time.sleep(0.7)
            continue
        except Exception as exc:
            failures.append(f"Openverse {query!r}: {type(exc).__name__}: {exc}")
            print(f"Scene {scene_index}: Openverse query failed for {query!r}: {type(exc).__name__}: {exc}")
            time.sleep(0.7)
            continue
        if not results:
            failures.append(f"Openverse {query!r}: no results")
        for result in results:
            try:
                return (*download_candidate(result, scene_index, work, query, "Openverse"), failures)
            except Exception as exc:
                failures.append(f"Openverse download: {type(exc).__name__}: {exc}")
                print(f"Scene {scene_index}: Openverse clip download failed: {type(exc).__name__}: {exc}")
        time.sleep(0.7)

    # Openverse's public API may not expose a video index; Commons is a secondary openly licensed source.
    for query in queries:
        if not query:
            continue
        try:
            results = commons_results(query)
        except Exception as exc:
            failures.append(f"Wikimedia Commons {query!r}: {type(exc).__name__}: {exc}")
            print(f"Scene {scene_index}: Wikimedia Commons query failed for {query!r}: {type(exc).__name__}: {exc}")
            time.sleep(0.7)
            continue
        if not results:
            failures.append(f"Wikimedia Commons {query!r}: no results")
        for result in results:
            try:
                return (*download_candidate(result, scene_index, work, query, "Wikimedia Commons"), failures)
            except Exception as exc:
                failures.append(f"Wikimedia Commons download: {type(exc).__name__}: {exc}")
                print(f"Scene {scene_index}: Wikimedia Commons clip download failed: {type(exc).__name__}: {exc}")
        time.sleep(0.7)
    return None, None, failures


def render_scene(scene, index, work):
    keyword = str(scene.get("image_keyword", "")).strip()
    text = str(scene.get("caption_text") or scene.get("text") or "").strip()
    source_path, attribution, failures = download_openverse(keyword, index + 1, work)
    clip_path = work / f"scene_{index:03d}.mp4"
    overlay_path = work / f"overlay_{index:03d}.png"
    make_caption_overlay(text).save(overlay_path)
    if source_path is None:
        print(f"Scene {index + 1}: CARD fallback for {keyword!r}; no stock-video download succeeded.")
        card_path = work / f"card_{index:03d}.png"
        make_card(text, keyword).save(card_path)
        video_input = ["-loop", "1", "-framerate", str(FPS), "-i", str(card_path)]
    else:
        print(f"Scene {index + 1}: REAL FOOTAGE ({attribution['provider']}) for {keyword!r}: {attribution['source_url']}")
        video_input = ["-i", str(source_path)]
    # Fit and crop to 9:16, then add a restrained zoom. The still-card path gets identical motion.
    frames = SCENE_SECONDS * FPS
    filter_graph = (
        f"[0:v]fps={FPS},scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},zoompan=z='min(zoom+0.00055,1.055)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"trim=duration={SCENE_SECONDS},setpts=PTS-STARTPTS,setsar=1[bg];"
        f"[1:v]format=rgba,fade=t=in:st=0:d=0.22:alpha=1[cap];"
        f"[bg][cap]overlay=0:0:shortest=1,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-loglevel", "error", *video_input, "-loop", "1", "-framerate", str(FPS), "-i", str(overlay_path),
         "-filter_complex", filter_graph, "-map", "[v]", "-an", "-t", str(SCENE_SECONDS), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25", "-threads", "2", "-pix_fmt", "yuv420p", str(clip_path)])
    return clip_path, attribution, failures


def main():
    script_path = ROOT / "script.json"
    if not script_path.exists():
        raise SystemExit("script.json is missing")
    data = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("script.json must contain at least one scene")
    for number, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or not str(scene.get("text", "")).strip():
            raise SystemExit(f"scene {number} needs non-empty text")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    work = OUTPUT / "render_tmp"
    work.mkdir(parents=True, exist_ok=True)
    clips, attributions, failures_by_scene = [], [], []
    for i, scene in enumerate(scenes):
        try:
            clip, attribution, source_failures = render_scene(scene, i, work)
            clips.append(clip)
            attributions.append({"scene": i + 1, "keyword": str(scene.get("image_keyword", "")), "attribution": attribution, "used_card": attribution is None})
            failures_by_scene.extend({"scene": i + 1, "failure": failure} for failure in source_failures)
        except Exception as exc:
            failure = f"Scene render fallback: {type(exc).__name__}: {exc}"
            failures_by_scene.append({"scene": i + 1, "failure": failure})
            # A bad source or decoder must not break the whole render. Retry the scene as a Pillow card.
            print(f"Scene {i + 1}: source/render failure, retrying as card: {type(exc).__name__}: {exc}")
            card_path = work / f"emergency_card_{i:03d}.png"
            make_card(str(scene.get("caption_text") or scene["text"]), str(scene.get("image_keyword", ""))).save(card_path)
            overlay_path = work / f"emergency_overlay_{i:03d}.png"
            make_caption_overlay(str(scene.get("caption_text") or scene["text"])).save(overlay_path)
            clip = work / f"scene_{i:03d}.mp4"
            graph = (f"[0:v]zoompan=z='min(zoom+0.00055,1.055)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
                     f"trim=duration={SCENE_SECONDS},setpts=PTS-STARTPTS[bg];[1:v]format=rgba,"
                     f"fade=t=in:st=0:d=0.22:alpha=1[cap];[bg][cap]overlay=0:0,format=yuv420p[v]")
            run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(card_path),
                 "-loop", "1", "-framerate", str(FPS), "-i", str(overlay_path), "-filter_complex", graph,
                 "-map", "[v]", "-an", "-t", str(SCENE_SECONDS), "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast",
                 "-crf", "25", "-threads", "2", "-pix_fmt", "yuv420p", str(clip)])
            clips.append(clip)
            attributions.append({"scene": i + 1, "keyword": str(scene.get("image_keyword", "")), "attribution": None, "used_card": True})
        time.sleep(0.7)

    # Hard cuts preserve the requested exact 4 seconds per scene and a 60-second 15-scene reel.
    concat_file = work / "concat.txt"
    concat_file.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    silent = work / "joined.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)])
    final_path = OUTPUT / "final.mp4"
    duration = len(scenes) * SCENE_SECONDS
    music = ROOT / "music.mp3"
    if music.is_file():
        audio_input = ["-stream_loop", "-1", "-i", str(music)]
        audio_filter = f"[1:a]atrim=duration={duration},asetpts=PTS-STARTPTS,volume=0.72,afade=t=out:st={max(0, duration-1.4)}:d=1.4[a]"
        print("Using music.mp3 with an automatic end fade.")
    else:
        audio_input = ["-f", "lavfi", "-i", f"sine=frequency=174:sample_rate=44100:duration={duration}"]
        audio_filter = f"[1:a]volume=0.018,afade=t=out:st={max(0, duration-1.4)}:d=1.4[a]"
        print("music.mp3 not found; using a quiet ambient tone.")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), *audio_input, "-filter_complex", audio_filter,
         "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(final_path)])

    metadata = OUTPUT / "attributions.json"
    metadata.write_text(json.dumps({"title": data.get("title", ""), "sources": attributions, "source_failures": failures_by_scene}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    real = sum(not item.get("used_card", False) for item in attributions)
    cards = len(scenes) - real
    print(f"Render complete: {real} scenes with real stock footage, {cards} card scenes; {duration}s total.")
    print(f"Attribution metadata: {metadata.relative_to(ROOT)}")
    print(f"Source failures logged: {len(failures_by_scene)}")
    print("Hashtags:", " ".join(str(tag) for tag in data.get("hashtags", [])))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Render-level infrastructure errors should be explicit; per-scene network issues are handled above.
        raise SystemExit(f"Render failed: {type(exc).__name__}: {exc}")
