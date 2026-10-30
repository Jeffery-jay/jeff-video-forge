# Build log

## 2026-10-30
- Corrected the footage source after confirming `https://api.openverse.org/v1/videos/` returns HTTP 404; the live API root and reference pages expose image/audio routes, with no documented video search endpoint. Removed Openverse attempts from rendering.
- Reworked Wikimedia Commons search to explicitly require video MIME results, use a descriptive project User-Agent and at least 1.2 seconds between HTTP requests, filter candidates to 40 MB, rank by keyword overlap and smaller size, and stream downloads with a hard size cap. Added a second Commons category-search path using `Category:Stock media` and keyword category results, with a strict relevance gate so poor matches fall back to Pillow cards.
- Added per-scene footage/card and source filename logs, plus `output/render-report.json` with scene source, filename, attribution, totals, and sourcing failures. Retained `output/attributions.json`, `output/final.mp4`, existing tone/music, and the unchanged Telegram workflow step.
- Upgraded weekly trend research from food-video ideas to complete Nigerian short-form comedy skits. Added Naija comedy theme/sound queries, deterministic FORMAT A/B alternation, renderer-compatible draft-script.json with timing, dialogue, captions, and SFX, and a no-Telegram execution path. Preserved workflow name, triggers, and script.json production handoff.

## 2026-10-30 - ECC quality layer
- Distilled ECC GAN planner/evaluator + reviewer patterns into prompts/skit-quality.md (plan -> critic pass -> write, hook/pacing/twist rubric)
- research.py: both Gemini and OpenRouter prompts now load the quality layer
