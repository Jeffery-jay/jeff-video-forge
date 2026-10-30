# Mama Ada Kitchen video maker

This free GitHub Actions workflow renders `script.json` as a 9:16 food reel using FFmpeg and Pillow. It uses the open-license Inter font bundled in `fonts/`, bundled local stock video clips, outlined captions, Ken Burns motion, and gentle crossfades. Rendering needs no Pexels API key or other footage API.

## Bundled stock footage

Short, compressed food and cooking clips are included in `footage/`, keeping the repository small. `footage/CREDITS.md` records each source URL and its license. The clips are provided under the Pexels License, which permits many free commercial uses but is not CC0; review its restrictions and the clips themselves before publishing. Scenes select local clips by matching `image_keyword` to clip filenames. If a matching file is missing, the renderer falls back to a generated gradient card for that scene.

## Optional music

Place a track you are licensed to use at the repository root as `music.mp3` and commit it. The render loops/limits it to the video's length and fades the end. Without that file, the renderer uses a quiet generated ambient tone. No music is fetched automatically.

## Weekly trend research

A separate GitHub Actions agent runs every Monday at 07:00 UTC, or manually from **Actions → Weekly trend research → Run workflow**. It checks `topics.json` with Google Trends for Nigeria using `pytrends` and best-effort public TikTok Creative Center hashtag/music pages over plain HTTP. Those pages may return only a JavaScript shell, and the sources do not guarantee complete trend rankings or exact viral metrics.

The agent reads `trends/trends.md` as prior context, then uses the existing Gemini Flash pattern and repository secret `GEMINI_API_KEY` to select one Nigerian/African comedy premise and write a complete Lagos skit. It alternates FORMAT A and FORMAT B by workflow run-number parity, falling back to date parity. The output keeps `title`, scenes with renderer-required `text` and `image_keyword`, `caption`, and `hashtags` compatible with `render.py`, with extra timing, dialogue, speaker, captions, and SFX fields. The brief is saved to `trends/trends-YYYY-MM-DD.md` and `trends/trends.md`; the full draft is saved to `draft-script.json`, never replacing production `script.json` or triggering rendering. Outputs are committed using the GitHub Actions token. Telegram delivery is intentionally skipped. If Gemini is unavailable, a renderer-compatible fallback skit is still written; it is a creative draft, not a verified trend claim.

## Make and receive a video

1. Edit `script.json`; every scene needs `text` and `image_keyword`. Keep JSON syntax valid and use specific visual phrases such as `jollof rice cooking`, `nigerian food closeup`, or `plantain frying`.
2. Commit changes to `script.json`, `render.py`, fonts, workflow or README to start a render, or open **Actions → Render video → Run workflow**.
3. When it finishes, download `mama-ada-kitchen-video` from the workflow run to get `output/final.mp4`.
4. To send videos to Telegram, add repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under **Settings → Secrets and variables → Actions**. If either is missing, delivery is skipped while the artifact is still uploaded.
5. Review the video, then post it manually to Instagram with the caption and hashtags from `script.json`.

## Telegram approval buttons

The APPROVE/REJECT buttons can be connected to a Cloudflare Worker. Follow [SETUP.md](SETUP.md) to deploy the webhook manually. Decision logging to `decisions.json` is optional and requires a GitHub personal access token stored as the Cloudflare Worker secret `GITHUB_TOKEN`; without it, Telegram still updates the message and sends a summary, but no GitHub decision log is written.
