const REPOSITORY = "Jeffery-jay/jeff-video-forge";
const DECISIONS_PATH = "decisions.json";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return Response.json({
        ok: true,
        message: "JeffForgeBot approval webhook",
        webhook_url: `${url.origin}/webhook`,
      });
    }

    if (url.pathname !== "/webhook") {
      return new Response("Not found", { status: 404 });
    }
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }
    if (!env.TELEGRAM_BOT_TOKEN) {
      return new Response("Missing TELEGRAM_BOT_TOKEN", { status: 500 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("Invalid JSON", { status: 400 });
    }

    const query = update.callback_query;
    if (!query) return Response.json({ ok: true });

    const choice = String(query.data || "").toLowerCase();
    if (choice !== "approve" && choice !== "reject") {
      await telegram(env, "answerCallbackQuery", {
        callback_query_id: query.id,
        text: "Unknown decision",
        show_alert: true,
      });
      return Response.json({ ok: true });
    }

    const approved = choice === "approve";
    const verdict = approved ? "APPROVED" : "REJECTED";
    const caption = approved
      ? "APPROVED ✅ by Jeff"
      : "REJECTED ❌, revisions needed";
    const message = query.message;
    const chatId = message?.chat?.id;

    await telegram(env, "answerCallbackQuery", {
      callback_query_id: query.id,
      text: verdict,
    });

    if (!message || chatId === undefined) {
      return Response.json({ ok: true, warning: "Callback had no message" });
    }

    const videoMessage = message.video || message.animation || message.document;
    if (videoMessage && message.caption !== undefined) {
      await telegram(env, "editMessageCaption", {
        chat_id: chatId,
        message_id: message.message_id,
        caption,
        reply_markup: { inline_keyboard: [] },
      });
    } else {
      await telegram(env, "editMessageText", {
        chat_id: chatId,
        message_id: message.message_id,
        text: caption,
        reply_markup: { inline_keyboard: [] },
      });
    }

    let logNote = "Decision logging is not configured yet.";
    if (env.GITHUB_TOKEN) {
      try {
        await logDecision(env.GITHUB_TOKEN, {
          verdict,
          approved,
          decided_at: new Date().toISOString(),
          repository: REPOSITORY,
          run_id: findRunId(message),
          telegram_chat_id: chatId,
          telegram_message_id: message.message_id,
          telegram_user_id: query.from?.id ?? null,
          telegram_username: query.from?.username ?? null,
        });
        logNote = "Decision saved to the repository.";
      } catch {
        logNote = "The decision was processed, but GitHub logging failed.";
      }
    }

    const summary = approved
      ? `Video approved by Jeff. ${logNote}`
      : `Video rejected by Jeff, revisions needed. ${logNote}`;
    await telegram(env, "sendMessage", { chat_id: chatId, text: summary });

    return Response.json({ ok: true });
  },
};

async function telegram(env, method, payload) {
  const response = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw new Error(`Telegram ${method} returned ${response.status}`);
  const result = await response.json();
  if (!result.ok) throw new Error(`Telegram ${method} failed`);
  return result.result;
}

function findRunId(message) {
  const text = `${message.text || ""}\n${message.caption || ""}`;
  const match = text.match(/github\.com\/[^/]+\/[^/]+\/actions\/runs\/(\d+)/i);
  return match ? match[1] : null;
}

async function logDecision(token, entry) {
  const apiBase = `https://api.github.com/repos/${REPOSITORY}/contents/${DECISIONS_PATH}`;
  const headers = {
    accept: "application/vnd.github+json",
    authorization: `Bearer ${token}`,
    "content-type": "application/json",
    "x-github-api-version": "2022-11-28",
    "user-agent": "JeffForgeBot-approval-webhook",
  };

  const existingResponse = await fetch(apiBase, { headers });
  let decisions = [];
  let sha;
  if (existingResponse.status === 200) {
    const file = await existingResponse.json();
    sha = file.sha;
    const decoded = atob(file.content.replace(/\s/g, ""));
    const bytes = Uint8Array.from(decoded, (character) => character.charCodeAt(0));
    decisions = JSON.parse(new TextDecoder().decode(bytes));
    if (!Array.isArray(decisions)) throw new Error("decisions.json must contain an array");
  } else if (existingResponse.status !== 404) {
    throw new Error(`GitHub read returned ${existingResponse.status}`);
  }

  decisions.push(entry);
  const encoded = toBase64(new TextEncoder().encode(`${JSON.stringify(decisions, null, 2)}\n`));
  const body = {
    message: `Record Telegram video decision: ${entry.verdict}`,
    content: encoded,
    ...(sha ? { sha } : {}),
  };
  const saveResponse = await fetch(apiBase, {
    method: "PUT",
    headers,
    body: JSON.stringify(body),
  });
  if (!saveResponse.ok) throw new Error(`GitHub write returned ${saveResponse.status}`);
}

function toBase64(bytes) {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
  }
  return btoa(binary);
}
