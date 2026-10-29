# Mama Ada Kitchen video maker

This free GitHub Actions workflow renders `script.json` as a 9:16 food reel using FFmpeg and Pillow. It uses the open-license Inter font bundled in `fonts/`, bundled local stock video clips, outlined captions, Ken Burns motion, and gentle crossfades. Rendering needs no Pexels API key or other footage API.

## Bundled stock footage

Short, compressed food and cooking clips are included in `footage/`, keeping the repository small. `footage/CREDITS.md` records each source URL and its license. The clips are provided under the Pexels License, which permits many free commercial uses but is not CC0; review its restrictions and the clips themselves before publishing. Scenes select local clips by matching `image_keyword` to clip filenames. If a matching file is missing, the renderer falls back to a generated gradient card for that scene.

## Optional music

Place a track you are licensed to use at the repository root as `music.mp3` and commit it. The render loops/limits it to the video's length and fades the end. Without that file, the renderer uses a quiet generated ambient tone. No music is fetched automatically.

## Weekly trend research

A separate GitHub Actions agent runs every Monday at 07:00 UTC, or manually from **Actions → Weekly trend research → Run workflow**. It reads the search topics in `topics.json`, best-effort checks Google Trends for Nigeria with `pytrends`, and fetches public TikTok Creative Center hashtag and music pages over plain HTTP. Those pages may return only a JavaScript shell, and these sources do not guarantee complete platform trend rankings or exact viral metrics.

The agent reads `trends/trends.md` as prior-week context, then uses the repository secret `GEMINI_API_KEY` with Gemini Flash to create a sourced trend brief and a proposed `draft-script.json` for Mama Ada Kitchen. If the secret is missing, or Gemini cannot return a valid response, it writes a template brief from the raw source results and does not create a draft script. The dated brief is saved as `trends/trends-YYYY-MM-DD.md`; the latest brief is also kept at `trends/trends.md` for continuity. Successful outputs are committed back to the repository by the script using the GitHub Actions token. It sends a review-ready summary through Telegram using `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` secrets. Add `GEMINI_API_KEY` under **Settings → Secrets and variables → Actions** to enable generated briefs and draft scripts. Research drafts are proposals only and do not replace `script.json` or trigger video rendering.

## Make and receive a video

1. Edit `script.json`; every scene needs `text` and `image_keyword`. Keep JSON syntax valid and use specific visual phrases such as `jollof rice cooking`, `nigerian food closeup`, or `plantain frying`.
2. Commit changes to `script.json`, `render.py`, fonts, workflow or README to start a render, or open **Actions → Render video → Run workflow**.
3. When it finishes, download `mama-ada-kitchen-video` from the workflow run to get `output/final.mp4`.
4. To send videos to Telegram, add repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under **Settings → Secrets and variables → Actions**. If either is missing, delivery is skipped while the artifact is still uploaded.
5. Review the video, then post it manually to Instagram with the caption and hashtags from `script.json`.

## Telegram approval buttons

The APPROVE/REJECT buttons can be connected to a Cloudflare Worker. Follow [SETUP.md](SETUP.md) to deploy the webhook manually. Decision logging to `decisions.json` is optional and requires a GitHub personal access token stored as the Cloudflare Worker secret `GITHUB_TOKEN`; without it, Telegram still updates the message and sends a summary, but no GitHub decision log is written.
