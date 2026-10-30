# Mama Ada Kitchen video maker

This free GitHub Actions workflow turns `script.json` into a short vertical video. It searches Openverse for openly licensed video per scene, tries a simplified keyword when needed, then checks Wikimedia Commons before falling back to the original Pillow scene card. FFmpeg crops footage to 9:16, adds subtle zoom motion and animated captions, and writes source, creator and license details to `output/attributions.json`. No API key is needed. Existing `music.mp3` is used when present; otherwise the quiet ambient tone remains.

## Make a video

1. Open `script.json` and edit the title, scenes, caption and hashtags. Each scene needs `text` and `image_keyword` fields. Keep the JSON punctuation and quotation marks valid.
2. Commit your change to the repository. A change to `script.json` automatically starts the render. You can also open the **Actions** tab, choose **Render video**, and select **Run workflow**.
3. When the run finishes, open it in **Actions** and download the `mama-ada-kitchen-video` artifact. The file is `output/final.mp4`.
4. To have GitHub send the video to Telegram, add repository secrets named `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in **Settings → Secrets and variables → Actions**. If either secret is missing, Telegram delivery is skipped. The video artifact is still uploaded.
5. Review the video first. Then post it manually to Instagram and use the caption and hashtags from `script.json`.

The included example is a Mama Ada Kitchen jollof rice post for Lagos. The workflow runs on GitHub's `ubuntu-latest` runner and has a five-minute job limit. GitHub's availability and usage limits apply to your account.
