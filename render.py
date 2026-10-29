#!/usr/bin/env python3
"""Render script.json as a vertical food reel with bundled local footage."""

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
WIDTH, HEIGHT = 1080, 1920
FPS = 24
SCENE_SECONDS = 4.0
CROSSFADE = 0.45
PEXELS_API = "https://api.pexels.com"


def run(args):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT)


def font(size, bold=False):
    bundled = ROOT / "fonts" / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf")
    fallback = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    for candidate in (bundled, Path(fallback)):
        if candidate.exists():
            loaded = ImageFont.truetype(str(candidate), size=size)
            if bold and hasattr(loaded, "set_variation_by_name"):
                try:
                    loaded.set_variation_by_name("Bold")
                except (OSError, ValueError):
                    pass
            return loaded
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


def make_card(scene_text, index, keyword):
    """Plain gradient fallback frame when no Pexels asset is available."""
    seed = sum(ord(ch) for ch in (keyword or scene_text))
    colors = [(89, 34, 22), (121, 48, 25), (45, 59, 39), (154, 82, 34)]
    base = colors[seed % len(colors)]
    image = Image.new("RGB", (WIDTH, HEIGHT), base)
    draw = ImageDraw.Draw(image, "RGBA")
    for i in range(12):
        x = (seed * (i + 7) * 37) % WIDTH
        y = (seed * (i + 11) * 53) % HEIGHT
        radius = 180 + (seed + 47 * i) % 300
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(245, 157, 66, 16))
    return image


def local_footage(keyword):
    """Pick the bundled clip whose filename best matches a scene keyword."""
    text = (keyword or "").lower().replace("_", "-")
    footage = ROOT / "footage"
    # Specific food matches precede generic cooking terms.
    groups = [
        ("plantain-frying.mp4", ("plantain", "banana")),
        ("food-plating.mp4", ("plating", "nigerian food", "food closeup", "serving")),
        ("grilled-chicken.mp4", ("chicken", "grilled", "fried chicken")),
        ("rice-cooking.mp4", ("jollof", "rice")),
        ("simmering-pot.mp4", ("sizzling", "pot", "simmer", "stew")),
        ("kitchen-cooking.mp4", ("kitchen", "cooking", "ambiance")),
    ]
    for filename, terms in groups:
        if any(term in text for term in terms):
            path = footage / filename
            if path.is_file():
                return path
    return None


def make_caption_overlay(text, index, title, hook):
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    accent = (255, 183, 95, 255)
    # A compact opening brand lockup and hook headline over the footage.
    if hook:
        draw.rounded_rectangle((76, 560, WIDTH-76, 1220), radius=44, fill=(8, 10, 9, 165), outline=(255, 255, 255, 50), width=2)
        draw.text((130, 620), "MAMA ADA KITCHEN  ·  LAGOS", font=font(30, True), fill=accent)
        y = 715
        for line in wrap_words(draw, title, font(66, True), WIDTH - 260)[:3]:
            draw.text((130, y), line, font=font(66, True), fill="white", stroke_width=2, stroke_fill=(0, 0, 0, 190))
            y += 88
    face = font(57, True)
    lines = wrap_words(draw, text, face, WIDTH - 220)[:3]
    line_height = 78
    panel_height = len(lines) * line_height + 76
    top = 1400 if hook else 1320
    draw.rounded_rectangle((62, top, WIDTH-62, top + panel_height), radius=34, fill=(0, 0, 0, 170), outline=(255, 255, 255, 60), width=2)
    y = top + 34
    for line in lines:
        draw.text((108, y), line, font=face, fill="white", stroke_width=3, stroke_fill=(0, 0, 0, 255))
        y += line_height
    return overlay


def stamp(seconds):
    ms = int(round(seconds * 1000))
    hh, ms = divmod(ms, 3_600_000)
    mm, ms = divmod(ms, 60_000)
    ss, ms = divmod(ms, 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"


def main():
    data_path = ROOT / "script.json"
    if not data_path.exists():
        raise SystemExit("script.json is missing")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    title = str(data.get("title", "Untitled video")).strip() or "Untitled video"
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("script.json must contain at least one scene")
    for number, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict) or not str(scene.get("text", "")).strip():
            raise SystemExit(f"scene {number} needs non-empty text")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    work = OUTPUT / "render_tmp"
    work.mkdir(parents=True, exist_ok=True)
    print("Using bundled local footage when a filename matches the scene keyword; no stock-footage API is used.")

    clips = []
    for i, scene in enumerate(scenes):
        text = str(scene["text"]).strip()
        keyword = str(scene.get("image_keyword", "")).strip()
        asset = local_footage(keyword)
        if asset:
            print(f"Scene {i + 1}: using footage/{asset.name} for {keyword!r}.")
        else:
            print(f"Scene {i + 1}: no bundled clip matches {keyword!r}; using generated card.")
        overlay_path = work / f"overlay_{i:03d}.png"
        make_caption_overlay(text, i, title, i == 0).save(overlay_path)
        clip_path = work / f"scene_{i:03d}.mp4"
        frames = int(SCENE_SECONDS * FPS)
        # A subtle, continuously moving zoom/pan makes both real clips and still photos feel alive.
        motion = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
                 f"zoompan=z='min(zoom+0.00065,1.075)':x='iw/2-(iw/zoom/2)+on*0.08':"
                 f"y='ih/2-(ih/zoom/2)+on*0.03':d=1:s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1")
        if asset is None:
            card_path = work / f"placeholder_{i:03d}.png"
            make_card(text, i, keyword).save(card_path)
            inputs = ["-loop", "1", "-framerate", str(FPS), "-i", card_path]
        else:
            inputs = ["-stream_loop", "-1", "-i", asset]
        vf = f"[0:v]{motion}[bg];[bg][1:v]overlay=0:0,format=yuv420p"
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-i", overlay_path,
             "-filter_complex", vf, "-t", SCENE_SECONDS, "-r", FPS, "-an", "-c:v", "libx264",
             "-preset", "ultrafast", "-crf", "24", "-threads", "2", clip_path])
        clips.append(clip_path)

    duration = len(scenes) * SCENE_SECONDS - max(0, len(scenes) - 1) * CROSSFADE
    inputs = []
    for clip in clips:
        inputs.extend(["-i", clip])
    chain = "[0:v]"
    output_label = "0:v"
    for i in range(1, len(scenes)):
        out = f"v{i}"
        offset = i * (SCENE_SECONDS - CROSSFADE)
        chain += f"[{i}:v]xfade=transition=fade:duration={CROSSFADE}:offset={offset:.3f}[{out}];"
        output_label = out
        chain += f"[{out}]" if i < len(scenes) - 1 else ""
    filter_complex = chain.rstrip(";") + f";[{output_label}]format=yuv420p[vout]"
    music = ROOT / "music.mp3"
    final_path = OUTPUT / "final.mp4"
    if music.exists():
        inputs.extend(["-stream_loop", "-1", "-i", music])
        audio_index = len(scenes)
        audio_filter = f"[{audio_index}:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,volume=0.72,afade=t=out:st={max(0, duration-1.4):.3f}:d={min(1.4, duration):.3f}[aout]"
        print("Using music.mp3 with an automatic end fade.")
    else:
        inputs.extend(["-f", "lavfi", "-i", f"sine=frequency=174:sample_rate=44100:duration={duration:.3f}"])
        audio_index = len(scenes)
        audio_filter = f"[{audio_index}:a]volume=0.018,afade=t=out:st={max(0, duration-1.4):.3f}:d={min(1.4, duration):.3f}[aout]"
        print("music.mp3 not found; using a quiet ambient tone, not a music track.")
    filter_complex += ";" + audio_filter
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", filter_complex,
         "-map", "[vout]", "-map", "[aout]", "-t", f"{duration:.3f}", "-c:v", "libx264",
         "-preset", "ultrafast", "-crf", "24", "-threads", "2", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", final_path])
    run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=s=x:p=0", final_path])
    print(f"Created {final_path.relative_to(ROOT)} from {len(scenes)} scenes at {WIDTH}x{HEIGHT}.")
    print("Hashtags:", " ".join(str(tag) for tag in data.get("hashtags", [])))


if __name__ == "__main__":
    main()
