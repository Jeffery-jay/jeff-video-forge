#!/usr/bin/env python3
"""Collect public food-video trend signals and draft a Mama Ada Kitchen brief."""

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
TOPICS_PATH = ROOT / "topics.json"
TRENDS_DIR = ROOT / "trends"
TODAY = date.today()


def fetch_text(url, timeout=20):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; MamaAdaTrendResearch/1.0)"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def collect_google_trends(topics):
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=60, timeout=(10, 25))
        batches = []
        for start in range(0, len(topics), 5):
            batch = topics[start:start + 5]
            if not batch:
                continue
            pytrends.build_payload(batch, timeframe="today 3-m", geo="NG")
            interest = pytrends.interest_over_time()
            if interest is None or interest.empty:
                batches.append({"topics": batch, "result": "No Google Trends interest data returned."})
                continue
            summary = {}
            for topic in batch:
                if topic in interest.columns:
                    series = interest[topic]
                    summary[topic] = {
                        "latest_interest": int(series.iloc[-1]),
                        "peak_interest": int(series.max()),
                        "recent_average": round(float(series.tail(4).mean()), 1),
                    }
            batches.append({"topics": batch, "weekly_interest": summary,
                            "source": "https://trends.google.com/trends/explore?geo=NG"})
        return {"status": "ok", "batches": batches}
    except Exception as exc:
        print(f"Google Trends unavailable ({type(exc).__name__}); continuing without it.", file=sys.stderr)
        return {"status": "unavailable", "detail": f"Google Trends request failed: {type(exc).__name__}"}


def collect_tiktok():
    urls = [
        "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en",
        "https://ads.tiktok.com/business/creativecenter/inspiration/popular/music/pc/en",
    ]
    records = []
    for url in urls:
        try:
            html = fetch_text(url)
            # Keep a small text sample only. TikTok may deliver a JS shell with no trend rows.
            text = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
            text = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            records.append({"url": url, "status": "fetched", "page_text_sample": text[:5000] or "No visible text; likely a client-rendered page."})
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            print(f"TikTok Creative Center fetch failed for {url}: {type(exc).__name__}", file=sys.stderr)
            records.append({"url": url, "status": "unavailable", "detail": type(exc).__name__})
    return records


def load_previous_week():
    previous = TRENDS_DIR / "trends.md"
    if not previous.exists():
        return "No previous trends/trends.md found."
    try:
        return previous.read_text(encoding="utf-8")[:10000]
    except OSError as exc:
        print(f"Could not read previous trend brief: {exc}", file=sys.stderr)
        return "Previous trend brief could not be read."


def template_brief(signals, previous):
    rows = [
        "# Weekly trend brief: Mama Ada Kitchen",
        f"\nResearch date: {TODAY.isoformat()}",
        "\n## Source status",
        f"\n- Google Trends: {signals['google_trends'].get('status', 'unknown')}",
        "- TikTok Creative Center: best-effort public page fetch; page text may be a JS shell rather than a live trend list.",
        "- Topics: " + ", ".join(signals["topics"]),
        "\n## Signal notes",
        "\nRaw public-source response summary:",
        "```json",
        json.dumps(signals, ensure_ascii=False, indent=2)[:12000],
        "```",
        "\n## Content strategies to test",
        "\n1. Open with a close food reveal or steam/sizzle visual in the first second, then name the craving. Source: Google Trends query set and TikTok Creative Center public inspiration pages; these fetches do not establish virality.",
        "2. Keep cuts brisk, with one clear cooking or plating action per scene. Source: strategy hypothesis from the queried food-reel topics, not a measured platform metric.",
        "3. Use a current-feeling, upbeat Afrobeats or amapiano-style sound only after checking that the track is available and licensed for the account. Source: topic seed `amapiano food video`; no specific track was verified.",
        "4. Build a simple transformation format: ingredients or pan, plated jollof, then a direct Lagos order invitation. Source: the Mama Ada Kitchen brief and topic seeds `jollof rice reel` and `lagos food vendor instagram`.",
        "\nThese are testable creative hypotheses, not verified claims about current viral posts. Configure GEMINI_API_KEY to generate an evidence-aware brief and a draft script.",
    ]
    if previous and previous != "No previous trends/trends.md found.":
        rows += ["\n## Continuity", "\nLast week's brief was read for continuity. No automated comparison was generated in template fallback."]
    return "\n".join(rows), None


def gemini_generation(signals, previous, api_key):
    import urllib.error
    prompt = f"""You are a careful social-video trend researcher for Mama Ada Kitchen, a Lagos restaurant. Use only the supplied signal data and prior brief. Distinguish direct evidence from hypotheses. Never claim view counts, viral status, current rankings, or a specific trending song unless the supplied source explicitly shows it. Cite source URLs beside claims and mark inaccessible or JavaScript-shell pages clearly.

Return ONLY valid JSON with exactly these top-level keys: trend_brief (Markdown string), draft_script (object). The trend_brief must document 3-5 actionable content strategies and cover hook style, pacing, sound type and format; cite supplied source URLs and separate observations from recommendations. The draft_script must match this schema: {{\"title\": string, \"scenes\": [{{\"text\": string, \"image_keyword\": string}}], \"caption\": string, \"hashtags\": [string]}}. Make a practical short food reel for Mama Ada Kitchen in Lagos based on the strongest supported trend signal. Use 3-5 scenes. Do not instruct copying a creator or using unlicensed music.

TODAY: {TODAY.isoformat()}
TREND SIGNALS:
{json.dumps(signals, ensure_ascii=False)}
PRIOR WEEK BRIEF:
{previous[:10000]}
"""
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}}).encode()
    request = Request(endpoint, data=body, headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    try:
        with urlopen(request, timeout=90) as response:
            result = json.load(response)
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        brief, script = parsed.get("trend_brief"), parsed.get("draft_script")
        if not isinstance(brief, str) or not isinstance(script, dict):
            raise ValueError("Gemini returned an incomplete brief or script")
        validate_script(script)
        return brief, script
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Gemini generation failed: {type(exc).__name__}: {exc}") from exc


def validate_script(script):
    required = ("title", "scenes", "caption", "hashtags")
    if any(key not in script for key in required):
        raise ValueError("draft script is missing required schema fields")
    if not isinstance(script["scenes"], list) or not script["scenes"]:
        raise ValueError("draft script scenes must be a non-empty list")
    for scene in script["scenes"]:
        if not isinstance(scene, dict) or not scene.get("text") or not scene.get("image_keyword"):
            raise ValueError("each scene needs text and image_keyword")


def commit_outputs():
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True, cwd=ROOT)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True, cwd=ROOT)
    subprocess.run(["git", "add", "-A", "--", "trends/"], check=True, cwd=ROOT)
    draft_path = ROOT / "draft-script.json"
    if draft_path.exists():
        subprocess.run(["git", "add", "-A", "--", "draft-script.json"], check=True, cwd=ROOT)
    else:
        subprocess.run(["git", "rm", "--cached", "-f", "draft-script.json"], check=False, cwd=ROOT)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if changed.returncode == 0:
        print("No research outputs changed; no commit created.")
        return
    if changed.returncode != 1:
        raise RuntimeError("Could not inspect staged research output changes")
    subprocess.run(["git", "commit", "-m", "Add weekly trend research"], check=True, cwd=ROOT)
    subprocess.run(["git", "push"], check=True, cwd=ROOT)
    print("Research outputs committed to the repository.")


def send_telegram(summary):
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram delivery skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return False
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": summary, "disable_web_page_preview": True}).encode()
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if result.get("ok") is not True:
            raise RuntimeError("Telegram API returned ok=false")
        print("Telegram accepted the research summary.")
        return True
    except Exception as exc:
        raise RuntimeError(f"Telegram send failed: {type(exc).__name__}") from exc


def main():
    topics = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    if not isinstance(topics, list) or not topics:
        raise SystemExit("topics.json must contain a non-empty array of search terms")
    previous = load_previous_week()
    signals = {
        "date": TODAY.isoformat(),
        "topics": topics,
        "google_trends": collect_google_trends(topics),
        "tiktok_creative_center": collect_tiktok(),
    }
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            brief, script = gemini_generation(signals, previous, api_key)
            mode = "Gemini"
            draft_status = "Draft script generated with Gemini."
        except RuntimeError as exc:
            print(f"{exc}; using template fallback.", file=sys.stderr)
            brief, script = template_brief(signals, previous)
            mode = "template fallback"
            draft_status = "Draft script skipped because Gemini generation failed."
    else:
        brief, script = template_brief(signals, previous)
        mode = "template fallback"
        draft_status = "Draft script skipped because GEMINI_API_KEY is not configured."

    TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    daily_path = TRENDS_DIR / f"trends-{TODAY.isoformat()}.md"
    daily_path.write_text(brief.rstrip() + "\n", encoding="utf-8")
    # A rolling alias enables continuity on subsequent weekly runs.
    (TRENDS_DIR / "trends.md").write_text(brief.rstrip() + "\n", encoding="utf-8")
    if script is not None:
        (ROOT / "draft-script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        # Do not leave a stale draft that could be mistaken for this week's result.
        stale = ROOT / "draft-script.json"
        if stale.exists():
            stale.unlink()

    summary = (f"Mama Ada Kitchen trend research is ready for review ({TODAY.isoformat()}).\n"
               f"Trend brief: trends/{daily_path.name}\n"
               f"Mode: {mode}. {draft_status}\n"
               "Review the brief and draft in the Jeffery-jay/jeff-video-forge repository before production.")
    commit_outputs()
    telegram_sent = send_telegram(summary)
    if not telegram_sent:
        raise RuntimeError("Research completed but Telegram summary was not delivered.")
    print(f"Research complete. Mode: {mode}. Brief: {daily_path.relative_to(ROOT)}. Telegram sent: {telegram_sent}.")


if __name__ == "__main__":
    main()
