#!/usr/bin/env python3
"""Render script.json into a 9:16 captioned slideshow video using Pillow and FFmpeg."""

import json
import math
import os
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
WIDTH, HEIGHT = 720, 1280
FPS = 24
SCENE_SECONDS = 4


def run(args):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT)


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap_words(draw, text, face, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), test, font=face)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]


def make_card(title, scene_text, index, count, keyword):
    # Create an original, keyword-seeded abstract food-color backdrop, without stock assets.
    seed = sum(ord(ch) for ch in (keyword or scene_text))
    colors = [(100, 30, 17), (154, 61, 22), (52, 76, 45), (196, 111, 45)]
    base = colors[seed % len(colors)]
    image = Image.new("RGB", (WIDTH, HEIGHT), base)
    draw = ImageDraw.Draw(image, "RGBA")
    for i in range(9):
        x = (seed * (i + 7) * 37) % WIDTH
        y = (seed * (i + 11) * 53) % HEIGHT
        radius = 130 + (seed + 47 * i) % 220
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(245, 157, 66, 13))
    # Dark translucent panel for legibility.
    draw.rounded_rectangle((48, 350, WIDTH-48, 1010), radius=34, fill=(12, 12, 12, 158))
    small = font(27, True)
    headline = font(49, True)
    body = font(39)
    draw.text((78, 390), title[:54], font=small, fill=(255, 205, 135, 255))
    draw.text((78, 445), f"{index + 1:02d} / {count:02d}", font=small, fill=(255, 255, 255, 205))
    lines = wrap_words(draw, scene_text, headline, WIDTH - 156)
    y = 535
    for line in lines[:5]:
        draw.text((78, y), line, font=headline, fill="white", stroke_width=1, stroke_fill=(0, 0, 0, 110))
        y += 65
    keyword_lines = wrap_words(draw, f"Fresh in Lagos  •  {keyword}", body, WIDTH - 156)
    y = max(y + 32, 875)
    for line in keyword_lines[:2]:
        draw.text((78, y), line, font=body, fill=(255, 225, 185, 255))
        y += 52
    return image


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
    subtitle_rows = []
    for i, scene in enumerate(scenes):
        start, end = i * SCENE_SECONDS, (i + 1) * SCENE_SECONDS
        card = make_card(title, str(scene["text"]).strip(), i, len(scenes), str(scene.get("image_keyword", "")))
        still_path = work / f"scene_{i:03d}.png"
        card.save(still_path)
        # Each still gets a gentle zoom-in Ken Burns effect.
        frame_path = work / f"scene_{i:03d}.mp4"
        frames = SCENE_SECONDS * FPS
        vf = (
            f"scale=800:1422,"
            f"zoompan=z='min(zoom+0.0007,1.06)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
            f"setsar=1,format=yuv420p"
        )
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", still_path,
             "-vf", vf, "-t", SCENE_SECONDS, "-r", FPS, "-an", "-c:v", "libx264",
             "-preset", "ultrafast", "-crf", "25", frame_path])
        subtitle_rows.append((start, end, str(scene["text"]).strip()))

    concat_path = work / "concat.txt"
    concat_path.write_text("".join(f"file '{(work / f'scene_{i:03d}.mp4').as_posix()}'\n" for i in range(len(scenes))), encoding="utf-8")
    silent_video = work / "slideshow.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_path,
         "-c", "copy", silent_video])

    # SubRip subtitles are embedded in the picture so playback needs no sidecar file.
    srt = work / "captions.srt"
    def stamp(seconds):
        ms = int(round(seconds * 1000))
        hh, ms = divmod(ms, 3_600_000)
        mm, ms = divmod(ms, 60_000)
        ss, ms = divmod(ms, 1000)
        return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"
    blocks = []
    for i, (start, end, text) in enumerate(subtitle_rows, start=1):
        blocks.extend([str(i), f"{stamp(start)} --> {stamp(end - 0.15)}", text, ""])
    srt.write_text("\n".join(blocks), encoding="utf-8")

    # Use a supplied music file if present, otherwise generate a quiet synthesized tone bed.
    music = next((p for p in [ROOT / "music.mp3", ROOT / "music.wav", ROOT / "music.m4a"] if p.exists()), None)
    final_path = OUTPUT / "final.mp4"
    subtitle_filter = f"subtitles={srt.as_posix()}:force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=105'"
    if music:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent_video, "-i", music,
             "-vf", subtitle_filter, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
             "-preset", "ultrafast", "-crf", "25", "-c:a", "aac", "-b:a", "96k",
             "-shortest", "-movflags", "+faststart", final_path])
    else:
        duration = len(scenes) * SCENE_SECONDS
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent_video,
             "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=44100:duration={duration}",
             "-vf", subtitle_filter, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
             "-preset", "ultrafast", "-crf", "25", "-c:a", "aac", "-b:a", "48k",
             "-shortest", "-movflags", "+faststart", final_path])

    # Verify a readable MP4 was produced and report basic metadata to the action log.
    run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=s=x:p=0", final_path])
    caption = str(data.get("caption", "")).strip()
    hashtags = data.get("hashtags", [])
    print(f"Created {final_path.relative_to(ROOT)} from {len(scenes)} scenes. Caption: {caption}")
    print("Hashtags:", " ".join(str(tag) for tag in hashtags))


if __name__ == "__main__":
    main()
