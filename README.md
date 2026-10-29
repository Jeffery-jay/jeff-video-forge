# Mama Ada Kitchen video maker

This free GitHub Actions workflow renders `script.json` as a 9:16 food reel using FFmpeg and Pillow. It uses the open-license Inter font bundled in `fonts/`, animated vertical footage or photos when available, outlined captions, and gentle crossfades. No paid APIs are used. Rendering is configured for `ubuntu-latest` with a five-minute job limit.

## Enable real Pexels footage (optional, free)

1. Create a free API key at https://www.pexels.com/api/ and follow Pexels' current account and license terms.
2. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Name it exactly `PEXELS_API_KEY` and paste the key as the secret value. Never commit the key to a file.
4. Run the workflow. It searches Pexels videos first, then photos, using each scene's `image_keyword`. If the secret is missing, a search has no matches, or a lookup/download fails, the scene uses a clean generated gradient fallback with the same title/caption overlay, so the workflow can still finish.

Pexels results depend on the keyword and API availability. Review the resulting video and the applicable asset licensing before posting.

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
