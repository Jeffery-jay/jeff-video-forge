# Telegram approval webhook setup

This adds a free Cloudflare Worker that handles the existing APPROVE and REJECT buttons sent by the render workflow. No Cloudflare deployment is performed for you. The Telegram bot token stays in Cloudflare, not in this repository.

## 1. Create the Worker

1. Sign in to the Cloudflare dashboard and open **Workers & Pages**.
2. Choose **Create application**, then **Create Worker**.
3. Give it a name such as `jeff-video-approval` and choose **Deploy** to create the starter Worker.
4. Open the new Worker and choose **Edit code**.
5. Select all the starter code, replace it with the complete contents of `telegram-webhook.js` in this repository, then choose **Deploy**.

## 2. Add the bot token as a secret

1. In the Worker, open **Settings → Variables and Secrets** (in some dashboard layouts this appears under **Settings → Variables**).
2. Choose **Add**, select **Secret**, and enter the variable name exactly as `TELEGRAM_BOT_TOKEN`.
3. Paste the existing JeffForgeBot token into the secret value field in Cloudflare. Do not paste the token into GitHub, source code, README, or chat.
4. Save the secret and deploy the Worker again if Cloudflare asks.

## 3. Copy the Worker webhook URL

1. Open the Worker URL in a browser, for example `https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/`.
2. The page responds with JSON containing `webhook_url`. Copy that exact URL. It ends in `/webhook`.

## 4. Tell Telegram to send updates to the Worker

Replace `YOUR_BOT_TOKEN` with the existing bot token and `YOUR_WORKER_WEBHOOK_URL` with the exact `webhook_url` you copied. Open this URL in your browser (or run it from a terminal):

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook?url=YOUR_WORKER_WEBHOOK_URL
```

For example, if the Worker homepage returns `https://jeff-video-approval.example.workers.dev/webhook`, the `url` value must be that exact full address. Telegram should return JSON with `"ok":true`. Treat the token as private: do not share or save the completed setWebhook URL in a public place, because the bot token is part of its path.

## 5. Test an approval

1. Trigger one render from **GitHub → Actions → Render video → Run workflow**. Make sure the existing GitHub Actions secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set, so the finished video is sent to Telegram with its buttons.
2. Tap **APPROVE** on that video message.
3. The message caption should become `APPROVED ✅ by Jeff`, and JeffForgeBot should send a summary in the same Telegram chat. **REJECT** changes the caption to `REJECTED ❌, revisions needed` and sends its own summary.

## Optional GitHub decision log

Without a GitHub token in the Cloudflare Worker settings, decisions still update the Telegram message and send the chat summary, but are not saved to GitHub. To enable the optional `decisions.json` log, create a GitHub fine-grained personal access token limited to this repository with **Contents: Read and write** permission. Add it in the Worker as a **Secret** named `GITHUB_TOKEN`, then deploy the Worker again. The token is only used by the Worker to read and update `decisions.json`. Never put it in this repository or share it in chat.
