#!/usr/bin/env python3
"""Research Nigerian short-form comedy signals and draft a complete skit."""

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


def fallback_skit(signals):
    fmt_a = date.fromisoformat(signals["date"]).toordinal() % 2 == 0
    if fmt_a:
        title, hook, setting = "DNA Test at Ojuelegba", "Attention! Every baby born here must take a DNA test before boarding!", "Ojuelegba bus park"
        lines = [("ANNOUNCER",hook,"gasp"),("MAMA TITI","My pikin get my nose, na my husband I no sure again!","record scratch"),("CONDUCTOR","Oga, I only dey work here. Why una dey look my face?","crowd murmur"),("PASSENGER","I no get baby, but test my goat. E resemble my landlord!","goat bleat"),("MAMA TITI","My baby born for Surulere, but him dey cry with Ajah accent!","baby crying"),("PASSENGER","I just come buy pure water, I no know anybody here!","running footsteps"),("ANNOUNCER","Late test fee na fifty thousand!","cash register"),("CONDUCTOR","Who announce this thing?","whistle"),("MAMA TITI","Conductor, bring your own birth certificate!","record scratch"),("CONDUCTOR","My mama know my papa, I swear!","nervous laugh"),("OFFICER","Nobody move. I be the official DNA inspector!","siren"),("OFFICER","Conductor, you are the first person we dey test today.","dramatic sting"),("CONDUCTOR","Please test the goat first!","goat bleat"),("MAMA TITI","Lagos bus stop: even your excuse need evidence!","laugh track"),("ANNOUNCER","Follow for more wahala. Result loading!","meme outro")]
        caption = "DNA test at Ojuelegba bus park? Lagos people no dey disappoint 😂"
        characters = ["announcer", "Mama Titi", "bus conductor", "passengers", "official"]
    else:
        title, hook, setting = "The Fire Payout", "Babe, the fire don finish. I thank God say you survive.", "Surulere flat"
        lines = [("WIFE",hook,"distant siren"),("HUSBAND","Na God save me. I think say everything don burn.","cough"),("WIFE","Forget the chair and TV. You dey okay?","soft piano"),("HUSBAND","I dey. Na only my slippers and phone remain.","sigh"),("WIFE","Thank God. I was shaking when I hear the news.","quiet crying"),("HUSBAND","You still come back for me, my love.","warm music"),("WIFE","Of course. You are more important than property.","gentle gasp"),("HUSBAND","I knew you loved me pass money matter.","soft laugh"),("WIFE","Insurance says each family gets ten million. You collect?","record scratch"),("HUSBAND","Ten million? I never hear anything like that.","gasp"),("WIFE","You survived and still missed the payout?","dramatic sting"),("HUSBAND","I was busy trying to stay alive!","cough"),("WIFE","Next time, read the policy before you run out!","record scratch"),("HUSBAND","Next time? You want another fire?","nervous laugh"),("WIFE","No. I want you to read the small print, my dear.","laugh track")]
        caption = "Love is patient. But did you read the insurance policy? 😂"
        characters = ["wife", "husband"]
    scenes = []
    for i, (speaker, line, sfx) in enumerate(lines):
        start = i * 4; end = start + 4
        timing = f"00:{start // 60:02d}:{start % 60:02d}-00:{end // 60:02d}:{end % 60:02d}"
        scenes.append({"text": line, "image_keyword": setting + ", Nigerian comedy scene", "timing": timing, "speaker": speaker, "dialogue": line, "caption_text": line, "sfx": sfx})
    return {"title": title, "hook": hook, "format": "A" if fmt_a else "B", "duration_seconds": 60, "characters": characters, "scenes": scenes, "caption": caption, "hashtags": ["#NaijaComedy", "#LagosSkit", "#NigerianTikTok", "#NaijaSkit", "#ComedySkits"]}

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
    script = fallback_skit(signals)
    rows += ["\n## Skit selected", "\nFormat " + script["format"] + ": " + script["title"] + ". Template fallback is a creative draft, not a verified trend claim."]
    return "\n".join(rows), script


def gemini_generation(signals, previous, api_key):
    import urllib.error
    run_no = int(os.getenv("GITHUB_RUN_NUMBER", "0") or 0)
    parity = (run_no if run_no else TODAY.toordinal()) % 2
    format_name = "A" if parity == 1 else "B"
    quality_path = ROOT / "prompts" / "skit-quality.md"
    try:
        quality_layer = quality_path.read_text(encoding="utf-8")
    except OSError:
        quality_layer = "(quality layer file missing: rely on the built-in rubric above.)"
    prompt = f"""You are a Nigerian short-form comedy trend researcher and skit writer. Research supplied public signals for Nigerian/African comedy themes and sounds. Distinguish observed source text from hypotheses. Never invent rankings, counts, virality, exact songs, or trending status. Mark JavaScript-shell pages clearly. Recommend only sounds the creator can verify and license.

First silently PLAN the skit (outline: premise, hook, beats, twist), then CRITICIZE it as a harsh Lagos audience member using the quality layer below, fix the weakest parts, and only then write the final skit. Never output the outline or critique.
Pick exactly ONE strong, realistic Lagos premise, then write a COMPLETE original 60-second comedy skit, not a content idea or food ad. Alternate formats deterministically: use GitHub run number parity when available, otherwise date parity. Required format: FORMAT {format_name} (parity {parity}).

QUALITY LAYER (from prompts/skit-quality.md, must all pass):
{{quality_layer}}
FORMAT A: shocking public announcement in the first 5 seconds, mass panic escalating through absurd excuses, punchline confrontation, authority-figure twist, meme outro.
FORMAT B: quiet domestic two-character setup, empathetic escalation, one dark ironic twist landing on a single greed punchline, laughing meme outro. Keep it fictional and non-graphic.
Both: realistic Lagos setting, natural pidgin-flavored dialogue, hook, characters, timed scene-by-scene dialogue, an SFX cue per beat, on-screen caption text per scene, posting caption and hashtags. Use 15 scenes of 4 seconds each. Each scene MUST contain non-empty string text and image_keyword for render.py, with timing, speaker, dialogue, caption_text, and sfx as safe extra fields. Root keys include title, scenes, caption, hashtags, and may include hook, format, duration_seconds, characters. No other root keys. render.py reads title, scene text/image_keyword, caption and hashtags. Keep overlay text concise. Do not copy creators or use unlicensed music.

Return ONLY valid JSON with exactly root keys trend_brief (Markdown) and draft_script (object). Brief gives source-aware observations/recommendations about premise, format, pacing, sound; cite supplied URLs, label hypotheses, note unavailable sources. draft_script is the complete skit.

TODAY: {TODAY.isoformat()}
RUN NUMBER: {run_no or "unavailable"}
REQUIRED FORMAT: {format_name}
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
        if not isinstance(scene, dict) or not isinstance(scene.get("text"), str) or not scene["text"].strip() or not isinstance(scene.get("image_keyword"), str) or not scene["image_keyword"].strip():
            raise ValueError("each scene needs non-empty text and image_keyword strings")
    if not isinstance(script["caption"], str) or not isinstance(script["hashtags"], list):
        raise ValueError("caption must be a string and hashtags a list")


def openrouter_generation(signals, previous, api_key):
    """Fallback brain: OpenRouter free model, same JSON contract as Gemini."""
    run_no = int(os.getenv("GITHUB_RUN_NUMBER", "0") or 0)
    parity = (run_no if run_no else TODAY.toordinal()) % 2
    format_name = "A" if parity == 1 else "B"
    quality_path = ROOT / "prompts" / "skit-quality.md"
    try:
        quality_layer = quality_path.read_text(encoding="utf-8")
    except OSError:
        quality_layer = "(quality layer file missing: rely on the built-in rubric above.)"
    prompt = f"""You are a Nigerian short-form comedy trend researcher and skit writer. Research supplied public signals for Nigerian/African comedy themes and sounds. Distinguish observed source text from hypotheses. Never invent rankings, counts, virality, exact songs, or trending status.

First silently PLAN the skit (outline: premise, hook, beats, twist), then CRITICIZE it as a harsh Lagos audience member using the quality layer below, fix the weakest parts, and only then write the final skit. Never output the outline or critique.
Pick exactly ONE strong, realistic Lagos premise, then write a COMPLETE original 60-second comedy skit, not a content idea or food ad. Required format: FORMAT {format_name}.

QUALITY LAYER (from prompts/skit-quality.md, must all pass):
{{quality_layer}}
FORMAT A: shocking public announcement in the first 5 seconds, mass panic escalating through absurd excuses, punchline confrontation, authority-figure twist, meme outro.
FORMAT B: quiet domestic two-character setup, empathetic escalation, one dark ironic twist landing on a single greed punchline, laughing meme outro. Keep it fictional and non-graphic.
Both: realistic Lagos setting, natural pidgin-flavored dialogue, hook, characters, timed scene-by-scene dialogue, an SFX cue per beat, on-screen caption text per scene, posting caption and hashtags. Use 15 scenes of 4 seconds each. Each scene MUST contain non-empty string text and image_keyword for render.py, with timing, speaker, dialogue, caption_text, and sfx as safe extra fields. Root keys include title, scenes, caption, hashtags, and may include hook, format, duration_seconds, characters. No other root keys. Keep overlay text concise. Do not copy creators or use unlicensed music.

Return ONLY valid JSON with exactly root keys trend_brief (Markdown) and draft_script (object). draft_script is the complete skit.

TODAY: {TODAY.isoformat()}
REQUIRED FORMAT: {format_name}
TREND SIGNALS (summary):
{json.dumps({"date": signals.get("date"), "topics": signals.get("topics"), "google_trends_status": signals.get("google_trends", {}).get("status")}, ensure_ascii=False)}
PRIOR WEEK BRIEF (first 3000 chars):
{previous[:3000]}
"""
    body = json.dumps({"model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                       "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.4, "max_tokens": 16000,
                       "reasoning": {"effort": "low"},
                       "response_format": {"type": "json_object"}}).encode()
    request = Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                      headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    with urlopen(request, timeout=120) as response:
        result = json.load(response)
    choice = result["choices"][0]
    if choice.get("finish_reason") == "length":
        raise ValueError("OpenRouter response truncated (increase max_tokens or shorten prompt)")
    text = choice["message"]["content"].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("OpenRouter returned no JSON object")
        parsed = json.loads(text[start:end + 1])
    brief, script = parsed.get("trend_brief"), parsed.get("draft_script")
    if not isinstance(brief, str) or not isinstance(script, dict):
        raise ValueError("OpenRouter returned an incomplete brief or script")
    validate_script(script)
    return brief, script


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
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        try:
            brief, script = gemini_generation(signals, previous, api_key)
            mode = "Gemini"
            draft_status = "Draft script generated with Gemini."
        except (RuntimeError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"{exc}; trying OpenRouter fallback.", file=sys.stderr)
            if openrouter_key:
                try:
                    brief, script = openrouter_generation(signals, previous, openrouter_key)
                    mode = "OpenRouter fallback"
                    draft_status = "Draft script generated with OpenRouter after Gemini failed."
                except Exception as exc2:
                    print(f"OpenRouter fallback failed: {type(exc2).__name__}: {exc2}; using template fallback.", file=sys.stderr)
                    brief, script = template_brief(signals, previous)
                    mode = "template fallback"
                    draft_status = "Draft script skipped because Gemini and OpenRouter both failed."
            else:
                brief, script = template_brief(signals, previous)
                mode = "template fallback"
                draft_status = "Draft script skipped because Gemini failed and no OPENROUTER_API_KEY is configured."
    elif openrouter_key:
        try:
            brief, script = openrouter_generation(signals, previous, openrouter_key)
            mode = "OpenRouter"
            draft_status = "Draft script generated with OpenRouter."
        except Exception as exc:
            print(f"OpenRouter generation failed: {type(exc).__name__}; using template fallback.", file=sys.stderr)
            brief, script = template_brief(signals, previous)
            mode = "template fallback"
            draft_status = "Draft script skipped because OpenRouter generation failed."
    else:
        brief, script = template_brief(signals, previous)
        mode = "template fallback"
        draft_status = "Draft script skipped because no LLM key is configured."

    TRENDS_DIR.mkdir(parents=True, exist_ok=True)
    daily_path = TRENDS_DIR / f"trends-{TODAY.isoformat()}.md"
    daily_path.write_text(brief.rstrip() + "\n", encoding="utf-8")
    # A rolling alias enables continuity on subsequent weekly runs.
    (TRENDS_DIR / "trends.md").write_text(brief.rstrip() + "\n", encoding="utf-8")
    if script is not None:
        (ROOT / "draft-script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Production handoff: render.yml triggers on script.json pushes.
        (ROOT / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        # Do not leave a stale draft that could be mistaken for this week's result.
        stale = ROOT / "draft-script.json"
        if stale.exists():
            stale.unlink()

    if script is not None:
        summary = (f"New skit draft: {script['title']} ({TODAY.isoformat()}).\n"
                   f"Format {script.get('format', '?')}: {script['caption']}\n"
                   "APPROVE by running the Render video workflow; it posts the rendered video to Telegram.")
    else:
        summary = (f"Mama Ada Kitchen trend research is ready for review ({TODAY.isoformat()}).\n"
                   f"Trend brief: trends/{daily_path.name}\n"
                   f"Mode: {mode}. {draft_status}")
    commit_outputs()
    send_telegram(summary)
    print(f"Research complete. Mode: {mode}. Brief: {daily_path.relative_to(ROOT)}. Draft: {script['title'] if script else 'none'}.")


if __name__ == "__main__":
    main()
