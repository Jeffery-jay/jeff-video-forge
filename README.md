# Mama Ada Kitchen video maker

This free GitHub Actions workflow renders `script.json` as a 9:16 food reel using FFmpeg and Pillow. It uses the open-license Inter font bundled in `fonts/`, bundled local stock video clips, outlined captions, Ken Burns motion, and gentle crossfades. Rendering needs no Pexels API key or other footage API.

## Bundled stock footage

Short, compressed food and cooking clips are included in `footage/`, keeping the repository small. `footage/CREDITS.md` records each source URL and its license. The clips are provided under the Pexels License, which permits many free commercial uses but is not CC0; review its restrictions and the clips themselves before publishing. Scenes select local clips by matching `image_keyword` to clip filenames. If a matching file is missing, the renderer falls back to a generated gradient card for that scene.

## Optional music

Place a track you are licensed to use at the repository root as `music.mp3` and commit it. The render loops/limits it to the video's length and fades the end. Without that file, the renderer uses a quiet generated ambient tone. No music is fetched automatically.

## Make and receive a video

1. Edit `script.json`; every scene needs `text` and `image_keyword`. Keep JSON syntax valid and use specific visual phrases such as `jollof rice cooking`, `nigerian food closeup`, or `plantain frying`.
2. Commit changes to `script.json`, `render.py`, fonts, workflow or README to start a render, or open **Actions → Render video → Run workflow**.
3. When it finishes, download `mama-ada-kitchen-video` from the workflow run to get `output/final.mp4`.
4. To send videos to Telegram, add repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under **Settings → Secrets and variables → Actions**. If either is missing, delivery is skipped while the artifact is still uploaded.
5. Telegram delivery includes the title, caption, hashtags and APPROVE/REJECT buttons. The buttons are displayed, but they do not process responses yet; that needs a separate webhook.
6. Review the video, then post it manually to Instagram with the caption and hashtags from `script.json`.

The included example is a Mama Ada Kitchen jollof rice post for Lagos. GitHub Actions availability and usage limits apply to your account.
