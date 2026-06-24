#!/usr/bin/env python3
"""
Veda Katha — standalone pipeline.
Story → Higgsfield images → ImageMagick composite → imgbb upload → Instagram post.
No n8n required. Run directly or via cron/tmux loop.

Usage:
    python3 pipeline.py                  # run once
    python3 pipeline.py --dry-run        # generate + composite, skip Instagram post
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.parse
import textwrap
from datetime import datetime
from pathlib import Path


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ─────────────────────────────────────────────
# CONFIG — edit these
# ─────────────────────────────────────────────
IG_USER_ID     = "17841411846641251"
IG_ACCESS_TOKEN = "EAAeUJMhQZBaABRmJ7Iub0T4JA6D6ZAJslzqh41nt9Mswc0GjyD9EVZBXCKZACgDnO1lgnRKWt7GQpP98YU9nFx1LlHWDG5r8Bub8zsrBWSFzhUJOUi5Yhcugqkw8hmQ6U6lpAICEApGs1ADPTMxYl17OMtHCxsKF7iZBhTCx3Sw3k961qaEGbum8y1s44"
IMGBB_API_KEY  = "432688a051897d9c333c761d48c60a9e"
REF_ELEMENT_ID = "92fa2bf7-f86d-4b0a-ba5a-1dc0792bcf52"

# Font paths — update if different on your system
TITLE_FONT = "/usr/share/fonts/custom/CormorantGaramond-Bold.ttf"
NARR_FONT  = "/usr/share/fonts/custom/DMSans-Regular.ttf"

# Log file — tracks recent posts to avoid repeats
LOG_FILE = Path(__file__).parent / "post_log.json"
TMP_DIR  = Path("/tmp/veda_pipeline")

# ─────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────

def load_recent_posts(n=15):
    if not LOG_FILE.exists():
        return "No recent posts. Full creative freedom."
    entries = json.loads(LOG_FILE.read_text())
    rows = entries[-n:]
    if not rows:
        return "No recent posts. Full creative freedom."
    lines = [f"{i+1}. Title: {r.get('title','')} | Theme: {r.get('theme','')} | Source: {r.get('source','')}"
             for i, r in enumerate(rows)]
    return "RECENT POSTS — DO NOT REPEAT:\n" + "\n".join(lines)


def build_prompt():
    recent = load_recent_posts()

    content_instructions = """
You are the creative director of "Vedic Vibes" — a premium Instagram carousel account that brings Hindu mythology to life through cinematic storytelling. Your content must feel like Amar Chitra Katha meets a high-budget mythological film campaign.

CHARACTER CONSISTENCY SYSTEM:
Before writing scene descriptions, create a CHARACTER SHEET for every character who appears in more than one slide.

DEITY SKIN COLOR — ACCURACY IS CRITICAL:
- Shiva / Mahadev: ash-white or pale grey skin. NEVER blue.
- Vishnu: very pale sky-blue or light blue skin.
- Krishna: deep sapphire blue or dark blue skin.
- Rama: greenish-blue tinged or olive-warm skin. NO peacock feather, NO flute — carries Kodanda bow.
- Durga: golden/fair skin. Kali = dark blue-black skin.
- Saraswati / Lakshmi: fair pale skin.
- Hanuman: orangish-brown or warm brown skin.
- Human / mortal characters: warm natural brown skin.

DEITY MANDATORY ATTRIBUTES:
- Shiva: third eye, crescent moon in matted jata, naga serpent, rudraksha mala, vibhuti ash, trishul.
- Vishnu: four arms, Sudarshana Chakra, Panchajanya conch, Kaumodaki mace, Padma lotus.
- Krishna: peacock feather in crown, bamboo flute, sapphire skin, yellow pitambara dhoti.
- Durga: multiple arms with weapons, lion/tiger mount, red or orange sari.

DEITY NEGATIVE ATTRIBUTES — NEVER cross-contaminate:
- Rama: NO peacock feather, NO flute, NO four arms, NO chakra. Carries BOW only.
- Krishna: NO bow as primary weapon, NO trishul, NO third eye, NO ash marks.
- Shiva: NO peacock feather, NO flute, NO chakra. MATTED JATA hair only.
- Vishnu: NO third eye, NO trishul, NO matted hair. SMOOTH CROWN only.

IMAGE SAFETY — SELF-SANITIZATION:
The image generator REJECTS: blood, wounds, severed body parts, gore, nudity, graphic injury, weapons striking flesh, death depicted graphically. Convey drama through aftermath, symbolic objects, witness reactions, atmospheric tension.

TRANSFORMATION/MOKSHA SCENES:
- Subject's body and face must remain CLEARLY VISIBLE — no vines/roots/branches wrapping around subject
- Divine light emanates FROM subject outward — environment RECEDES, not encroaches
- Dissolving effects happen at EXTREMITIES only — face and torso stay solid and sharp

NARRATIVE FLOW — MINI AMAR CHITRA KATHA:
5 slides: OPENING → RISING → TURNING → CLIMAX → RESOLUTION
Narration voice: plain declarative sentences, simple past tense, like actual Amar Chitra Katha caption boxes.
BAD: "From stone, he came. Not summoned. Not invoked."
GOOD: "Narasimha burst from the pillar. Hiranyakashipu had claimed no god could stop him."
"""

    carousel_thinking = """CAROUSEL THINKING:
STEP 1: Choose a story with clear arc — compelling character, conflict, meaningful resolution.
STEP 2: Map to 5 beats: Opening → Rising → Turning → Climax → Resolution.
STEP 3: Write all 5 narrations FIRST (140-150 chars each, split into 3 lines <=42 chars).
STEP 4: Write visual scenes. Each scene illustrates that narration moment.
STEP 5: Each narration (except slide 5) must end on tension that compels swipe."""

    json_schema = """{
  "post_type": "carousel",
  "title": "compelling 2-4 word title",
  "theme": "3-5 word topic for logging",
  "source": "Vedic source — e.g. Bhagavata Purana 8.7",
  "caption": "full caption with spiritual insight and CTA (max 2500 chars)",
  "hashtags": ["25 hashtag strings without # symbol"],
  "characters": {
    "character_name": {
      "identity": "who they are",
      "skin": "EXACT skin tone",
      "face": "4-5 specific features",
      "hair": "style, length, color, ornaments",
      "clothing": "exact garments",
      "distinctive": "mandatory deity attributes"
    }
  },
  "slides": [
    {
      "slide_number": 1,
      "narrative_role": "OPENING",
      "narration": "EXACTLY 140-150 characters.",
      "narration_lines": ["line 1 <=42 chars", "line 2 <=42 chars", "line 3 <=42 chars"],
      "scene": "Character appearance first (verbatim from sheet), then action, environment, emotion."
    }
  ]
}"""

    image_prompt_rules = """
For EACH slide, write a "image_prompt" field with a complete Higgsfield image prompt:

--- CHARACTER ---
[Full name], [EXACT skin tone + light interaction], [build], [hair in atmosphere], wearing [worn garment with frayed edges dissolving into fog], [tarnished gold jewelry], [ALL deity attributes]. [Divine weapon if present].

--- ACTION + CAMERA ---
[Pose, gesture, expression]
[Camera: extreme low angle / low hero shot / tight portrait / back view / symmetrical frontal]

SCALE RULE — large structures (mountains, palaces, cosmic forms):
- Structure fills upper 70-80% of frame, character tiny at base (bottom 15-20%)
- Extreme low-angle camera looking UP
- Structure extends BEYOND frame edges — peak lost in clouds

MOUNT/RIDER RULE:
- Rider and mount face SAME direction as one unified silhouette
- Specify: "both facing camera-left" or "both facing camera-right"

--- ENVIRONMENT + LIGHTING ---
[Tactile aged surfaces: chipped stone / soot-blackened walls / cracked basalt / moss steps]
LIGHTING SETUP:
  Source: [brass oil lamp / ritual fire / divine weapon glow / cave opening / low sun]
  Direction: [top-left / side / behind / below]
  Temperature: [warm amber / cold blue-green / ember orange] on face and hands ONLY
  Falloff: harsh — beyond 8-10 feet dissolves into complete darkness
  Fill: NONE — crushed blacks acceptable
  Interaction: light scatters through volumetric fog creating god rays
  Contrast: extreme — most frame dark, light reveals only subject

--- ATMOSPHERE (3-4 elements, ALL mandatory) ---
- VOLUMETRIC FOG — thick, swirling, ground-hugging, hides ground and lower body
- Floating dust/ash particles in the single light shaft
- Smoke — incense, ritual fire, atmospheric
- God rays cutting through volumetric fog

--- MANDATORY FEEL ---
Sacred mythic cinematic art. Volumetric fog throughout. Selective detail — face and hands sharp, background dissolves. Tactile aged materials. One motivated warm light source. Extreme contrast crushed blacks. Film grain. Strong vignette. Ancient, sacred, emotionally weighty.
Keep bottom 30% darker/atmospheric for text overlay. NO TEXT in image."""

    json_schema = json_schema.replace(
        '"scene": "Character appearance first (verbatim from sheet), then action, environment, emotion."',
        '"scene": "Character appearance first (verbatim from sheet), then action, environment, emotion.",\n      "image_prompt": "Complete self-contained image generation prompt following the rules above."'
    )

    return (
        content_instructions
        + "\n\nUSER REQUEST:\n\n"
        + recent
        + "\n\nCreate an original Instagram CAROUSEL from Hindu Puranas, Upanishads, Bhagavad Gita, or Vedic tradition.\n\n"
        + carousel_thinking
        + "\n\nIMAGE PROMPT RULES (include image_prompt in each slide):\n"
        + image_prompt_rules
        + "\n\nOUTPUT FORMAT — respond ONLY with this JSON:\n"
        + json_schema
        + "\nNo markdown. No explanation."
    )


# ─────────────────────────────────────────────
# CLAUDE CLI
# ─────────────────────────────────────────────

def run_claude(prompt, timeout=1200):
    log("[claude] Starting Claude CLI — generating story JSON...")
    prompt_file = TMP_DIR / "prompt.txt"
    prompt_file.write_text(prompt)
    log(f"[claude] Prompt written ({len(prompt)} chars). Calling claude -p ...")

    env = os.environ.copy()
    env["NO_COLOR"] = "1"

    start = time.time()
    stop_heartbeat = threading.Event()

    def heartbeat():
        while not stop_heartbeat.wait(30):
            elapsed = int(time.time() - start)
            log(f"[claude] Still waiting... ({elapsed}s elapsed)")

    t = threading.Thread(target=heartbeat, daemon=True)
    t.start()

    try:
        proc = subprocess.Popen(
            ["claude", "-p", prompt, "--output-format", "json",
             "--max-turns", "1",
             "--model", "claude-haiku-4-5-20251001"],
            stdout=subprocess.PIPE, stderr=None,  # stderr streams live to terminal
            text=True, env=env
        )
        try:
            stdout, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise
    finally:
        stop_heartbeat.set()

    elapsed = int(time.time() - start)
    log(f"[claude] Finished in {elapsed}s. Return code: {proc.returncode}")

    if proc.returncode != 0:
        log(f"[claude] stdout: {stdout[:800]}")
        raise RuntimeError(f"Claude CLI failed (rc={proc.returncode}).")

    log(f"[claude] Raw stdout length: {len(stdout)} chars")
    try:
        cli_out = json.loads(stdout)
    except json.JSONDecodeError:
        log(f"[claude] Non-JSON stdout: {stdout[:500]}")
        raise RuntimeError("Claude CLI returned non-JSON output.")
    if cli_out.get("is_error"):
        log(f"[claude] Error in response: {json.dumps(cli_out.get('errors', []))}")
        raise RuntimeError(f"Claude returned error: {cli_out.get('errors')}")
    return cli_out.get("result", "")


def generate_images(slides, timeout=1200):
    log(f"[higgsfield] Generating {len(slides)} images sequentially...")
    image_urls = []

    for i, slide in enumerate(slides):
        prompt = slide.get("image_prompt") or slide.get("scene", "")
        if not prompt:
            raise RuntimeError(f"Slide {i+1} has no image prompt")
        prompt = f"<<<{REF_ELEMENT_ID}>>> {prompt}"

        log(f"[higgsfield] Submitting slide {i+1}/{len(slides)} (waiting for result)...")
        result = subprocess.run(
            ["higgsfield", "generate", "create", "gpt_image_2",
             "--prompt", prompt,
             "--aspect_ratio", "3:4",
             "--quality", "medium",
             "--resolution", "1k",
             "--wait",
             "--wait-timeout", "10m",
             "--json"],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"Higgsfield failed slide {i+1}: {result.stderr[:300]}")

        log(f"[higgsfield] Slide {i+1} raw: {result.stdout[:400]}")
        out = json.loads(result.stdout)
        if isinstance(out, list):
            out = out[0] if out else {}
        url = out.get("result_url") or \
              (out.get("results") or {}).get("rawUrl") or \
              (out.get("output") or {}).get("url") or \
              out.get("url") or out.get("image_url")
        if not url:
            raise RuntimeError(f"No URL in response: {result.stdout[:400]}")
        image_urls.append(url)
        log(f"[higgsfield] Slide {i+1} done: {url[:80]}")

    return image_urls


# ─────────────────────────────────────────────
# PARSE PIPELINE OUTPUT
# ─────────────────────────────────────────────

def parse_output(raw):
    def safe_parse(s):
        try:
            return json.loads(s)
        except Exception:
            pass
        match = re.search(r'\{[\s\S]*\}', s)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        raise ValueError(f"Cannot parse JSON from: {s[:300]}")

    parsed = safe_parse(raw.strip())

    content = parsed.get("content", parsed)
    content["post_type"] = "carousel"
    if not isinstance(content.get("hashtags"), list):
        content["hashtags"] = []
    content.setdefault("source", "Vedic Tradition")
    content.setdefault("theme", content.get("title", "Vedic Teaching"))

    roles = ["OPENING", "RISING", "TURNING", "CLIMAX", "RESOLUTION"]
    slides = content.get("slides", [])
    normalized = []
    for idx, s in enumerate(slides[:5]):
        narration = s.get("narration", "")
        lines = s.get("narration_lines", [])
        if not lines and narration:
            words = narration.split()
            cur = ""
            lines = []
            for w in words:
                if len((cur + " " + w).strip()) > 42:
                    lines.append(cur.strip())
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                lines.append(cur.strip())
            lines = lines[:3]
        normalized.append({
            "slide_number": idx + 1,
            "narrative_role": s.get("narrative_role", roles[idx]),
            "narration": narration,
            "narration_lines": lines,
            "scene": s.get("scene", ""),
            "image_prompt": s.get("image_prompt", ""),
        })
    content["slides"] = normalized
    return content


# ─────────────────────────────────────────────
# IMAGE COMPOSITING (ImageMagick)
# ─────────────────────────────────────────────

def composite_text(input_file, output_file, slide_num, slides, story_title):
    dims = subprocess.check_output(
        ["identify", "-format", "%wx%h", input_file]
    ).decode().strip().split("x")
    W, H = int(dims[0]), int(dims[1])

    LM         = round(W * 0.06)
    NARR_PT    = round(H * 0.022)
    NARR_LH    = round(NARR_PT * 1.5)
    BASELINE_Y = round(H * 0.92)
    TITLE_PT   = round(H * 0.038)
    FADE_START = round(H * 0.52)
    FADE_H     = H - FADE_START

    slide = slides[slide_num - 1] if slide_num <= len(slides) else {}
    text_lines = list(slide.get("narration_lines", []))[:3]
    if not text_lines:
        narration = slide.get("narration", "")
        words = narration.split()
        cur = ""
        for w in words:
            if len((cur + " " + w).strip()) > 42:
                text_lines.append(cur.strip())
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            text_lines.append(cur.strip())
        text_lines = text_lines[:3]

    fade_file = str(TMP_DIR / f"fade_{slide_num}.png")
    faded     = str(TMP_DIR / f"faded_{slide_num}.png")

    subprocess.run([
        "convert", "-size", f"{W}x{FADE_H}",
        "gradient:rgba(26,26,26,0)-rgba(26,26,26,153)",
        fade_file
    ], check=True)

    subprocess.run([
        "convert", input_file, fade_file,
        "-geometry", f"+0+{FADE_START}", "-composite", faded
    ], check=True)

    cmd = ["convert", faded,
           "-font", NARR_FONT,
           "-pointsize", str(NARR_PT),
           "-fill", "rgba(242,235,217,0.92)",
           "-kerning", "0.5"]

    for li in range(len(text_lines) - 1, -1, -1):
        line_idx = len(text_lines) - 1 - li
        y_pos = BASELINE_Y - (line_idx * NARR_LH)
        line = text_lines[li].replace('"', '\\"')
        cmd += ["-annotate", f"+{LM}+{y_pos}", line]

    if slide_num == 1:
        top_narr_y = BASELINE_Y - ((len(text_lines) - 1) * NARR_LH)
        title_y = top_narr_y - NARR_PT - round(TITLE_PT * 0.3)
        title_escaped = story_title.upper().replace('"', '\\"')
        cmd += [
            "-font", TITLE_FONT,
            "-pointsize", str(TITLE_PT),
            "-fill", "#F2EBD9",
            "-kerning", str(round(TITLE_PT * 0.12)),
            "-annotate", f"+{LM}+{title_y}", title_escaped
        ]

    cmd.append(output_file)
    subprocess.run(cmd, check=True)

    for f in [fade_file, faded]:
        try:
            os.remove(f)
        except Exception:
            pass


# ─────────────────────────────────────────────
# IMGBB UPLOAD
# ─────────────────────────────────────────────

def upload_imgbb(file_path):
    with open(file_path, "rb") as f:
        import base64
        encoded = base64.b64encode(f.read()).decode()

    data = urllib.parse.urlencode({
        "key": IMGBB_API_KEY,
        "image": encoded,
    }).encode()

    req = urllib.request.Request("https://api.imgbb.com/1/upload", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    if result.get("data", {}).get("url"):
        return result["data"]["url"]
    raise RuntimeError(f"imgbb upload failed: {result}")


# ─────────────────────────────────────────────
# INSTAGRAM POSTING
# ─────────────────────────────────────────────

def ig_post(image_urls, caption):
    base = "https://graph.facebook.com/v18.0"
    token = IG_ACCESS_TOKEN
    uid = IG_USER_ID

    log(f"[instagram] Creating {len(image_urls)} container(s)...")
    container_ids = []
    for url in image_urls:
        params = urllib.parse.urlencode({
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        }).encode()
        req = urllib.request.Request(f"{base}/{uid}/media", data=params, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read())
        cid = res.get("id")
        if not cid:
            raise RuntimeError(f"Failed to create container: {res}")
        container_ids.append(cid)
        time.sleep(1)

    log(f"[instagram] Containers: {container_ids}")
    time.sleep(5)

    params = urllib.parse.urlencode({
        "media_type": "CAROUSEL",
        "children": ",".join(container_ids),
        "caption": caption[:2200],
        "access_token": token,
    }).encode()
    req = urllib.request.Request(f"{base}/{uid}/media", data=params, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())
    carousel_id = res.get("id")
    if not carousel_id:
        raise RuntimeError(f"Failed to create carousel: {res}")

    log(f"[instagram] Carousel container: {carousel_id}. Waiting...")
    time.sleep(10)

    params = urllib.parse.urlencode({
        "creation_id": carousel_id,
        "access_token": token,
    }).encode()
    req = urllib.request.Request(f"{base}/{uid}/media_publish", data=params, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())

    post_id = res.get("id")
    log(f"[instagram] Posted! ID: {post_id}")
    return post_id


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def log_post(content, post_id):
    log = []
    if LOG_FILE.exists():
        log = json.loads(LOG_FILE.read_text())
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "post_id": post_id,
        "title": content.get("title", ""),
        "theme": content.get("theme", ""),
        "source": content.get("source", ""),
    })
    LOG_FILE.write_text(json.dumps(log, indent=2))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip Instagram posting")
    parser.add_argument("--test", action="store_true", help="Dry-run with 1 slide only")
    args = parser.parse_args()
    if args.test:
        args.dry_run = True

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}", flush=True)
    print(f"Veda Katha Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}", flush=True)
    print(f"{'='*50}\n", flush=True)

    # 1. Build + run prompt
    prompt = build_prompt()
    raw = run_claude(prompt)

    # 2. Parse content
    content = parse_output(raw)
    log(f"[parse] Story: '{content.get('title')}' | Slides: {len(content.get('slides', []))}")

    slides = content.get("slides", [])
    if not slides:
        raise RuntimeError("No slides in content. Check Claude output.")

    # 3. Generate images via Higgsfield CLI
    if args.test:
        slides = slides[:1]
        log("[test] Limiting to 1 slide")
    image_urls = generate_images(slides)
    log(f"[higgsfield] Got {len(image_urls)} image URLs")

    failed = [u for u in image_urls if not str(u).startswith("http")]
    if failed:
        raise RuntimeError(f"{len(failed)} images failed generation.")

    # 4. Download + composite text
    slides = content.get("slides", [])
    story_title = content.get("title", "VEDIC VIBES").upper()
    final_urls = []

    for i, url in enumerate(image_urls):
        slide_num = i + 1
        raw_file   = str(TMP_DIR / f"raw_{slide_num}.png")
        final_file = str(TMP_DIR / f"final_{slide_num}.png")

        log(f"[composite] Slide {slide_num}: downloading...")
        urllib.request.urlretrieve(url, raw_file)

        log(f"[composite] Slide {slide_num}: compositing text...")
        composite_text(raw_file, final_file, slide_num, slides, story_title)

        log(f"[composite] Slide {slide_num}: uploading to imgbb...")
        hosted_url = upload_imgbb(final_file)
        final_urls.append(hosted_url)
        log(f"[composite] Slide {slide_num}: {hosted_url}")

    # 5. Build caption
    hashtags = " ".join(f"#{h.lstrip('#')}" for h in content.get("hashtags", []))
    caption = content.get("caption", "") + ("\n\n" + hashtags if hashtags else "")

    if args.dry_run:
        log("[dry-run] Skipping Instagram post.")
        log(f"Caption preview: {caption[:300]}...")
        log(f"Image URLs: {final_urls}")
        log("[dry-run] COMPLETE — all steps passed.")
        return

    # 6. Post to Instagram
    post_id = ig_post(final_urls, caption)

    # 7. Log
    log_post(content, post_id)
    log(f"DONE — post ID {post_id}")


if __name__ == "__main__":
    main()
