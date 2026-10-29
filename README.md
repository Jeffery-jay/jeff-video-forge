# Mama Ada Kitchen video maker

This free GitHub Actions workflow turns `script.json` into a short vertical video. It uses Python and Pillow to make illustrated title cards, then FFmpeg to animate the cards, add subtitles and create the MP4. It does not use paid APIs or fetch stock photos. The `image_keyword` field is a visual prompt/label for each scene, not a stock-photo search.

## Make a video

1. Open `script.json` and edit the title, scenes, caption and hashtags. Each scene needs `text` and `image_keyword` fields. Keep the JSON punctuation and quotation marks valid.
2. Commit your change to the repository. A change to `script.json` automatically starts the render. You can also open the **Actions** tab, choose **Render video**, and select **Run workflow**.
3. When the run finishes, open it in **Actions** and download the `mama-ada-kitchen-video` artifact. The file is `output/final.mp4`.
4. To have GitHub send the rendered video to Telegram, add repository secrets named `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in **Settings → Secrets and variables → Actions**. If either secret is missing, Telegram delivery is skipped. The video artifact is still uploaded.
5. Telegram delivery includes the title, caption and hashtags from `script.json`. The APPROVE and REJECT buttons are displayed, but acting on them requires a small webhook/worker (Cloudflare) that will be added next. For now, delivery of the video is the milestone.
6. Review the video first. Then post it manually to Instagram and use the caption and hashtags from `script.json`.

The included example is a Mama Ada Kitchen jollof rice post for Lagos. The workflow runs on GitHub's `ubuntu-latest` runner and has a five-minute job limit. GitHub's availability and usage limits apply to your account.
