#!/usr/bin/env python3
"""
Build Veda Katha Reloaded v3 — reference-first pipeline.

Key change from v2: style is carried entirely by the Higgsfield reference element
(@vedic-vibes-style, 59 reference images). Image prompts are now SHORT — just the
reference tag + scene description + band template for text. No massive style text blob.
"""

import json
import copy
import uuid

with open('/Users/ashwin/Downloads/Veda Katha CLI.json') as f:
    wf = json.load(f)

wf.pop('id', None)
wf['name'] = 'Veda Katha Reloaded v3'

# ============================================================
# Helper: generate n8n-style UUID
# ============================================================
def uid():
    return str(uuid.uuid4())

# ============================================================
# NODES TO REMOVE
# ============================================================
REMOVE_NODES = [
    'Split Image Prompts',
    'Build Image Prompt',
    'Collect Image Prompts',
    'Write Image Prompts File',
    'Submit Images via CLI',
    'Extract Job IDs',
]

wf['nodes'] = [n for n in wf['nodes'] if n['name'] not in REMOVE_NODES]

# Also remove their connections (both as source and as target references)
for name in REMOVE_NODES:
    wf['connections'].pop(name, None)
for src in list(wf['connections'].keys()):
    for conn_type in wf['connections'][src]:
        for target_list in wf['connections'][src][conn_type]:
            wf['connections'][src][conn_type] = [
                [t for t in tl if t['node'] not in REMOVE_NODES]
                for tl in wf['connections'][src][conn_type]
            ]

# ============================================================
# 0. INJECT STYLE CONFIG into Image Style Guide Set node
#    v3: reference element carries style. Only pass IDs + narration rules.
# ============================================================
style_node = next(n for n in wf['nodes'] if n['name'] == 'Image Style Guide Set')

with open('/Users/ashwin/Documents/events/event/vedic_vibes_style.json') as sf:
    style_json = json.load(sf)

style_obj = {
    "referenceElementId": style_json['reference_element_id'],
    "narrationRules": style_json['narration_consistency_rules']
}
style_node['parameters']['jsonOutput'] = json.dumps(style_obj)


# ============================================================
# 1. UPDATE CONTENT INSTRUCTIONS — add character sheet + self-sanitization + story labels
# ============================================================
ci_node = next(n for n in wf['nodes'] if n['name'] == 'Content Instructions Set')
ci_obj = json.loads(ci_node['parameters']['jsonOutput'])
ci_text = ci_obj['contentInstructions']

new_sections = r"""

CHARACTER CONSISTENCY SYSTEM:
Before writing scene descriptions, create a CHARACTER SHEET for every character who appears in more than one slide. This sheet is included verbatim in every image prompt where that character appears.

DEITY SKIN COLOR — ACCURACY IS CRITICAL (Indian viewers will immediately reject wrong skin tones):
- Shiva / Mahadev: ash-white or pale grey skin. Sacred ash (vibhuti) marks. NEVER blue. Blue = Vishnu lineage only.
- Vishnu: very pale sky-blue or light blue skin.
- Krishna: deep sapphire blue or dark blue skin.
- Rama: greenish-blue tinged or olive-warm skin (varies by tradition — specify which).
- Durga / Kali: Durga = golden/fair skin. Kali = dark blue-black skin.
- Saraswati / Lakshmi: fair pale skin.
- Hanuman: orangish-brown or warm brown skin.
- Human / mortal characters: warm natural brown skin. NEVER blue/grey/supernatural unless explicitly cursed.

DEITY MANDATORY ATTRIBUTES (include ALL of these in every prompt for that deity):
- Shiva: third eye (trinetra) on forehead, crescent moon (Chandra) in matted jata, naga serpent coiled around neck, rudraksha mala, vibhuti ash marks, trishul.
- Vishnu: four arms, Sudarshana Chakra, Panchajanya conch, Kaumodaki mace, Padma lotus, Vaijayanti garland, Shrivatsa mark on chest.
- Krishna: peacock feather in crown, bamboo flute (bansuri), sapphire skin, yellow pitambara silk dhoti.
- Durga: multiple arms with weapons (trishul, sword, lotus, conch, chakra, bow), lion/tiger mount, red or orange sari.

DEITY NEGATIVE ATTRIBUTES — NEVER cross-contaminate between deities:
- Rama: NO peacock feather (that is Krishna ONLY), NO flute, NO four arms, NO chakra. Rama carries a BOW (Sharanga/Kodanda), NOT a flute.
- Krishna: NO bow as primary weapon (he carries it rarely), NO trishul, NO third eye, NO ash marks.
- Shiva: NO peacock feather, NO flute, NO chakra. Shiva has MATTED JATA hair, not a smooth topknot.
- Vishnu: NO third eye, NO trishul, NO matted hair. Vishnu has a SMOOTH CROWN, not jata.
- Hanuman: NO crown, NO jewelry (simple/minimal only), NO weapons other than mace (gada).
The image model tends to merge Hindu deity archetypes into a generic "Hindu god" with mixed attributes. Your character sheet MUST explicitly state what the character does NOT have if there is risk of confusion. For example, for Rama: "NO peacock feather, NO flute — carries Kodanda bow."

TRANSFORMATION/MOKSHA/DIVINE SCENES — SUBJECT CLARITY:
When depicting divine transformation, moksha, ascension, or transcendence:
- The subject's body and face must remain CLEARLY VISIBLE and UNOBSTRUCTED — no vines, roots, branches, or environmental elements wrapping around or covering the subject
- Divine light emanates FROM the subject outward — environment recedes, not encroaches
- Background elements (trees, architecture) stay in BACKGROUND — maintain clear separation between subject and environment
- If the scene involves nature (forest, river, mountain), push it to the edges/background. The subject occupies clear negative space in the center
- Dissolving/translucent effects happen at the EXTREMITIES only (fingertips, hair ends, garment edges) — face and torso stay solid and sharp

For each character define:
- Name and identity
- Exact skin tone (use deity rules above — be precise)
- Face: 4-5 specific features (jawline, eye shape, brow, nose, expression tendency)
- Hair: exact style, length, color, texture, ornaments
- Clothing: exact garments, colors, fabric condition — must cover torso
- ALL mandatory deity attributes for that character

CRITICAL — CHARACTER SHEET EMBEDDING RULES:
1. Every scene description MUST begin with the full character sheet description for ALL characters visible in that scene. Physical appearance first, action second, environment third.
2. The FIRST sentence of every scene MUST name the character and state their skin tone and clothing. This prevents the image model from defaulting to wrong archetypes.
3. Characters must look IDENTICAL across all 5 slides — same face, same skin tone, same clothing, same hair. If a character's appearance changes between slides (e.g. clothing torn in battle), explicitly describe the change AND re-state all unchanged features.
4. NEVER rely on the character's name alone to convey appearance. "Ekalavya draws his bow" will produce random results. "Ekalavya, a lean-muscled young man with warm deep brown skin, wild curly black hair, wearing an ochre dhoti and angavastra, draws his bow" will be consistent.

Include this character sheet in the JSON output as a top-level "characters" object.

IMAGE SAFETY — SELF-SANITIZATION:
Scene descriptions go directly to an image generator with strict safety filters. You must write safety-compliant descriptions yourself. Do NOT write violent/graphic descriptions expecting downstream cleanup.

The image generator REJECTS prompts containing: blood, wounds, severed body parts, gore, nudity, graphic physical injury, weapons striking flesh, death depicted graphically.

CHILD CHARACTERS — SAFETY FILTER TRIGGERS (learned from rejected generations):
The filter false-flags child figures easily. When a story features a child (Dhruva, Prahlad, child Krishna, etc.) you MUST:
- Describe them as a YOUNG BOY/GIRL "around eight years old" — NEVER "aged 5", "small child", "toddler", or "little".
- State they are FULLY CLOTHED in layered robes covering shoulders, chest and torso completely. NEVER "bare-chested", "small dhoti", or any minimal/partial clothing on a child.
- NEVER place a child in close physical contact with an adult/deity (no embracing, no hands on the child, no deity touching the child's body/forehead). Keep them at a respectful distance, or show the deity/adult ALONE with the child implied off-frame or replaced by a symbol (e.g. show Vishnu gesturing to the pole star rather than touching the boy).
- Prefer wide or back-view framing for children over tight close-ups.

Instead, convey dramatic moments through:
- Emotional aftermath: facial expressions, body posture, trembling hands
- Symbolic objects: a knife laid down, an offering at someone's feet, a crown removed
- Witness reactions: onlookers' faces showing shock, awe, grief
- Atmospheric tension: storm clouds, cracking earth, divine light overwhelming darkness
- Implied action: a warrior kneeling where he just stood, dust settling after impact

Example — Ekalavya's sacrifice:
BAD: "Ekalavya cuts off his thumb with a knife, blood dripping"
GOOD: "Ekalavya kneels before Drona, his right hand closed tight against his chest, a small wrapped offering at Drona's feet. His face radiates painful devotion — eyes wet but unwavering. Drona's expression shifts from stern demand to stunned recognition. A bow lies abandoned beside Ekalavya, never to be drawn the same way again."

NARRATIVE FLOW — MINI AMAR CHITRA KATHA:
This carousel must read like a mini Amar Chitra Katha comic. The viewer swipes through 5 slides and experiences a COMPLETE STORY — beginning, middle, end — with each slide advancing the narrative chronologically.

Each slide has TWO components:
1. SCENE (visual) — a cinematic illustration prompt. NO TEXT rendered in the image. Pure visual art.
2. NARRATION (text overlay) — 20-35 words of story prose, added as a text overlay AFTER image generation. This is the Amar Chitra Katha narration box.

The narration must:
- Tell a coherent, complete story across 5 slides that ANY reader can follow
- Flow chronologically — slide 1 begins the tale, slide 5 ends it
- Use PLAIN DECLARATIVE SENTENCES — simple past tense, matter-of-fact, like actual Amar Chitra Katha caption boxes. The image carries the drama. Captions just tell what happened.
- NO purple prose, NO dramatic fragments ("He came. Not summoned. Not invoked."), NO rhetorical questions, NO em-dashes for effect
- Include character dialogue in quotes where natural (e.g. "I teach only princes," said Drona.) — but only when it genuinely happened in the story
- Slide 5 narration delivers the moral or outcome plainly — what changed, what it meant

NARRATION VOICE EXAMPLES:
BAD (overdramatic): "From stone, he came. Not summoned. Not invoked. Just there, as he always had been."
GOOD (ACK style): "Narasimha burst from the pillar. Hiranyakashipu had claimed no god could stop him — now he knew he was wrong."

BAD: "A devotion so pure it shook the heavens themselves."
GOOD: "Prahlad refused to call his father God. No punishment could make him stop chanting Vishnu's name."

SLIDE STRUCTURE:
- Slide 1 (OPENING): Set the scene. Introduce the world and the central character. Hook the reader into the tale.
- Slide 2 (RISING): Introduce the conflict, challenge, or question. Stakes become clear.
- Slide 3 (TURNING): The moment of confrontation, choice, or test. Tension at maximum.
- Slide 4 (CLIMAX): The decisive action, sacrifice, revelation, or transformation.
- Slide 5 (RESOLUTION): The aftermath and meaning. What changed. The spiritual truth revealed.

IMPORTANT — SCENE DESCRIPTIONS MUST NOT INCLUDE ANY TEXT RENDERING INSTRUCTIONS.
Scene descriptions are PURELY VISUAL — describe only what the camera sees. Text overlay is handled separately by post-processing. Do not mention fonts, text placement, or typography in scene descriptions.
"""

ci_text = ci_text.replace(
    'OUTPUT RULE:\nAlways respond with ONLY valid JSON',
    new_sections + '\nOUTPUT RULE:\nAlways respond with ONLY valid JSON'
)
ci_obj['contentInstructions'] = ci_text
ci_node['parameters']['jsonOutput'] = json.dumps(ci_obj)


# ============================================================
# 2. UPDATE BUILD CONTENT PROMPT → BUILD MASTER PROMPT
#    Now includes image style guide + Higgsfield submission instructions
# ============================================================
bcp_node = next(n for n in wf['nodes'] if n['name'] == 'Build Content Prompt')
bcp_node['name'] = 'Build Master Prompt'

# Update all connections referencing old name
for src in list(wf['connections'].keys()):
    if src == 'Build Content Prompt':
        wf['connections']['Build Master Prompt'] = wf['connections'].pop(src)
    else:
        for conn_type in wf['connections'][src]:
            for tl in wf['connections'][src][conn_type]:
                for t in tl:
                    if t['node'] == 'Build Content Prompt':
                        t['node'] = 'Build Master Prompt'

bcp_node['parameters']['jsCode'] = r"""const contentInstructions = $('Content Instructions Set').first().json.contentInstructions || '';
const refId = $('Image Style Guide Set').first().json.referenceElementId || '';
const narrationRules = $('Image Style Guide Set').first().json.narrationRules || {};

const recentItems = $input.all();
const recentRows = recentItems
  .filter(i => i.json && (i.json.theme || i.json.title || i.json.source))
  .slice(0, 15);

let recentTopicsStr;
if (recentRows.length > 0) {
  const lines = recentRows.map((r, idx) => {
    const parts = [];
    if (r.json.title) parts.push('Title: ' + r.json.title);
    if (r.json.theme) parts.push('Theme: ' + r.json.theme);
    if (r.json.source) parts.push('Source: ' + r.json.source);
    return (idx + 1) + '. ' + parts.join(' | ');
  });
  recentTopicsStr = 'RECENT POSTS — DO NOT REPEAT:\n' + lines.join('\n');
} else {
  recentTopicsStr = 'No recent posts. Full creative freedom.';
}

const carouselThinking = `CAROUSEL THINKING — MINI AMAR CHITRA KATHA:

STEP 1: Choose a story with a clear arc — compelling character, conflict, meaningful resolution. 5 panels max.
STEP 2: Map to 5 beats: Opening → Rising → Turning → Climax → Resolution.
STEP 3: Write all 5 narrations FIRST (EXACTLY 140-150 chars each, then split each into 3 lines <=42 chars for narration_lines). Read back-to-back — must flow as coherent mini-story.
STEP 4: Write visual scenes. Each scene illustrates that narration's moment.
STEP 5: Cliffhanger check — each narration (except slide 5) must end on tension that compels swipe.`;

const jsonSchema = `OUTPUT FORMAT — respond ONLY with this JSON:
{
  "post_type": "carousel",
  "title": "compelling 2-4 word title",
  "theme": "3-5 word topic for logging",
  "source": "Vedic source — e.g. Bhagavata Purana 8.7",
  "caption": "full caption with spiritual insight and CTA (max 2500 chars)",
  "hashtags": ["25 hashtag strings without # symbol"],
  "characters": {
    "character_name": {
      "identity": "who they are",
      "skin": "EXACT skin — use deity color rules from instructions",
      "face": "4-5 specific features",
      "hair": "style, length, color, ornaments",
      "clothing": "exact garments",
      "distinctive": "mandatory deity attributes if applicable"
    }
  },
  "image_count": 5,
  "slides": [
    {
      "slide_number": 1,
      "narrative_role": "OPENING",
      "narration": "EXACTLY 140-150 characters. Story prose. Dialogue in quotes. Compels swipe.",
      "narration_lines": ["line 1 <=42 chars", "line 2 <=42 chars", "line 3 <=42 chars"],
      "scene": "What is happening in this scene — describe the moment, characters, environment, emotion. Keep it concise. The style reference handles the look."
    }
  ]
}

RULES:
- Exactly 5 slides. OPENING → RISING → TURNING → CLIMAX → RESOLUTION.
- scene: describe WHAT is happening. Character appearance first (verbatim from sheet), then action, environment, emotion. No style/rendering instructions — the reference element handles that.
- All 5 narrations must tell a complete story readable on their own.
- Slide 5 narration delivers closure + spiritual/moral insight.

NARRATION LENGTH — CRITICAL FOR TEXT CONSISTENCY:
- EVERY narration MUST be 140-150 characters (count them). Same length on every slide = same font size in every image.
- After writing each narration, split it into exactly 3 lines of <=42 characters each, breaking at word boundaries, and put them in "narration_lines".
- The image generator paints text at a size that fits — identical length + pre-broken lines is the ONLY way to lock font size and margin across slides.`;

const imageInstructions = `AFTER generating JSON, submit all 5 images to Higgsfield.

For EACH slide call generate_image with these params:
- model: "gpt_image_2"
- aspect_ratio: "3:4"
- quality: "medium"

IMPORTANT: Do NOT render any text, titles, captions, or narration into the image. Generate PURE VISUAL ART only. Text is added in post-processing.

BUILD EACH IMAGE PROMPT using this structure — every section matters for the mythic feel:

--- CHARACTER (from character sheet, skin tone FIRST) ---
[Full name], [EXACT skin tone + how this scene's light hits it], [build], [hair interacting with atmosphere — strands catching light, smoke, wind, volumetric fog], wearing [garment with rough worn texture, dust, frayed edges — fabric dissolving into surrounding fog/mist at extremities], [heavy tarnished gold jewelry with oxidized patina], [ALL deity attributes: third eye, crescent moon, naga, chakra, etc.]. [Divine weapon/object if present — emitting restrained warm glow].

--- ACTION + CAMERA ---
[What they are doing — pose, gesture, expression with luminous intense eyes]
[Camera: pick ONE — extreme low angle from ground / low hero shot at knee level / tight portrait close-up / back view over shoulder / symmetrical frontal for ceremonial]

SCALE RULE — for scenes with large structures (mountains, cosmic forms, palaces, giant beings):
- Switch to ENVIRONMENTAL framing: structure fills upper 70-80% of frame, character small at base (bottom 15-20%)
- Extreme low-angle camera at ground level looking UP to emphasize colossal scale
- Structure extends BEYOND frame edges — peak lost in clouds, sides cropped — implies size bigger than image can contain
- Use tiny human figures, animals, or trees near the base as scale anchors

MOUNT/RIDER RULE — when a character rides a mount (elephant, bull, eagle, chariot):
- Rider and mount face the SAME direction as one unified silhouette
- Rider's torso aligned with mount's spine, slightly turned toward camera
- Specify direction explicitly: "both facing camera-left" or "both facing camera-right"
- Mount's head, body, and rider must form a single coherent composition — no conflicting angles

--- ENVIRONMENT + LIGHTING (critical for mythic feel — use lighting style from vedic-vibes-style reference) ---
[Setting with TACTILE AGED surfaces: chipped stone / soot-blackened temple walls / cracked basalt / moss-covered steps / ancient carved reliefs weathered by centuries / cave rock]

LIGHTING SETUP — ONE single motivated sacred light source, matching the vedic-vibes-style reference:
  Source: [name it — brass oil lamp / ritual fire / divine weapon glow / cave opening / low sun through dust / temple doorway fire]
  Direction: [where light comes from — top-left / side / behind through doorway / below from fire]
  Temperature: [warm amber / cold blue-green / ember orange] on face and hands ONLY
  Falloff: harsh — everything beyond 8-10 feet dissolves into complete darkness
  Fill light: NONE — deep shadows on shadow side of face, crushed blacks acceptable
  Interaction: light scatters through volumetric fog and dust particles, creating visible god rays
  Contrast: extreme — most of the frame is dark, light reveals only the subject
NO clean surfaces, no studio lighting, no even illumination, no multiple competing light sources.

--- ATMOSPHERE (3-4 elements — must HIDE portions of the scene, use effects from vedic-vibes-style reference) ---
- VOLUMETRIC FOG — thick, swirling, ground-hugging mist that obscures the lower body and hides the ground. This is the signature atmospheric element — every image MUST have it
- Floating dust/ash/pollen particles visible in the single light shaft
- Smoke — incense, ritual fire, atmospheric — interacting with the subject
- Fabric edges dissolving into surrounding smoke and fog
- God rays / crepuscular rays cutting through the volumetric fog from the single light source
- Wind effects — hair streaming, fabric billowing, ash swirling
- Controlled darkness hiding the background — deep shadow as design tool

--- MANDATORY FEEL (append to every prompt — these reference the @vedic-vibes-style elements) ---
Sacred mythic cinematic art, matching the vedic-vibes-style reference. Volumetric fog and mist throughout — thick, swirling, hiding portions of the scene. Selective detail density — face and hands sharp, background dissolves into atmospheric darkness. Tactile aged materials throughout. One motivated warm light source. Extreme contrast with crushed blacks. Visible film grain. Strong vignette. Physically textured finish. Ancient, sacred, dangerous, emotionally weighty. Apply the lighting, atmosphere, color grading, and compositional style from the vedic-vibes-style reference <<<` + refId + `>>>.

Keep the bottom ~30% of the image darker/atmospheric (shadow, fog, controlled darkness) for text overlay in post-processing — but do NOT paint any text or gradient box.

Apply this style reference to all images: <<<` + refId + `>>>

CONSISTENCY RULES:
1. Character appearance identical across all 5 slides — same skin, hair, clothing, jewelry. Only pose/expression changes.
2. ONE motivated light source per slide — named explicitly.
3. 3-4 atmospheric effects per slide — all must HIDE portions of the scene.
4. Colors desaturated and ancient — antique gold not bright gold, dusty ochre not vivid.
5. All figures fully clothed — dhoti, angavastra, sari, torso covered. Family-safe.
6. NO TEXT in images — no titles, no captions, no narration, no typography of any kind.

Submit all 5. Return only:
{"content": {...full content JSON...}, "job_ids": ["uuid1","uuid2","uuid3","uuid4","uuid5"]}
No markdown. No explanation.`;

const userPrompt = recentTopicsStr +
  '\n\nCreate an original Instagram CAROUSEL from Hindu Puranas, Upanishads, Bhagavad Gita, or Vedic tradition.\n\n' +
  carouselThinking + '\n\n' +
  jsonSchema + '\n\n' +
  imageInstructions;

const combinedPrompt = contentInstructions + '\n\nUSER REQUEST:\n\n' + userPrompt;
return [{ json: { combinedPrompt } }];"""


# ============================================================
# 3. RENAME Generate Content via CLI → Execute Pipeline via CLI
#    Increase timeout to 600s
# ============================================================
gen_node = next(n for n in wf['nodes'] if n['name'] == 'Generate Content via CLI')
gen_node['name'] = 'Execute Pipeline via CLI'

# Update connections
for src in list(wf['connections'].keys()):
    if src == 'Generate Content via CLI':
        wf['connections']['Execute Pipeline via CLI'] = wf['connections'].pop(src)
    else:
        for conn_type in wf['connections'][src]:
            for tl in wf['connections'][src][conn_type]:
                for t in tl:
                    if t['node'] == 'Generate Content via CLI':
                        t['node'] = 'Execute Pipeline via CLI'

gen_node['parameters']['jsCode'] = r"""const { execSync } = require('child_process');
try {
  const stdout = execSync(
    'cat /tmp/n8n_content_prompt.txt | CLAUDE_CONFIG_DIR=/home/node/.n8n/.claude HOME=/home/node NO_COLOR=1 /usr/local/bin/claude --output-format json',
    { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024, timeout: 600000 }
  );
  return [{ json: { stdout } }];
} catch(e) {
  throw new Error('CLI failed: ' + (e.stderr || e.stdout || e.message).slice(0, 2000));
}"""


# ============================================================
# 4. UPDATE Parse Content Plan → Parse Pipeline Output
#    Now extracts content + job_ids from single CLI output
# ============================================================
parse_node = next(n for n in wf['nodes'] if n['name'] == 'Parse Content Plan')
parse_node['name'] = 'Parse Pipeline Output'

# Update connections
for src in list(wf['connections'].keys()):
    if src == 'Parse Content Plan':
        wf['connections']['Parse Pipeline Output'] = wf['connections'].pop(src)
    else:
        for conn_type in wf['connections'][src]:
            for tl in wf['connections'][src][conn_type]:
                for t in tl:
                    if t['node'] == 'Parse Content Plan':
                        t['node'] = 'Parse Pipeline Output'

parse_node['parameters']['jsCode'] = r"""function safeParse(str) {
  try { return JSON.parse(str); } catch (e) {}
  const block = str.match(/\{[\s\S]*\}$/m)?.[0] || str.match(/\{[\s\S]*\}/)?.[0];
  const src = block || str;
  let out = '', inStr = false, esc = false, i = 0;
  while (i < src.length) {
    const c = src[i], code = src.charCodeAt(i);
    if (esc) { out += c; esc = false; i++; continue; }
    if (c === '\\' && inStr) { out += c; esc = true; i++; continue; }
    if (c === '"') { inStr = !inStr; out += c; i++; continue; }
    if (!inStr && c === '/' && src[i+1] === '/') { while (i < src.length && src[i] !== '\n') i++; continue; }
    if (!inStr && c === '/' && src[i+1] === '*') { i += 2; while (i < src.length - 1 && !(src[i] === '*' && src[i+1] === '/')) i++; i += 2; continue; }
    if (inStr && code < 0x20) {
      if (c === '\n') out += '\\n';
      else if (c === '\r') out += '\\r';
      else if (c === '\t') out += '\\t';
      else out += '\\u' + code.toString(16).padStart(4, '0');
      i++; continue;
    }
    out += c; i++;
  }
  try { return JSON.parse(out); } catch (e) {
    throw new Error('Parse failed: ' + e.message + ' | Raw: ' + str.slice(0, 500));
  }
}

const raw = $input.first().json.stdout || '';
const cliOut = JSON.parse(raw);
const resultText = cliOut.result || '';

let parsed;
try {
  parsed = safeParse(resultText.trim());
} catch (e) {
  throw new Error('Parse failed: ' + e.message + ' | Raw: ' + resultText.slice(0, 500));
}

// Handle merged output: { content: {...}, job_ids: [...] }
let content, jobIds;
if (parsed.content && parsed.job_ids) {
  content = parsed.content;
  jobIds = parsed.job_ids;
} else if (parsed.slides && Array.isArray(parsed.slides)) {
  // Fallback: old format where content IS the top-level object
  content = parsed;
  jobIds = parsed.job_ids || [];
} else {
  content = parsed;
  jobIds = [];
}

// Normalize content
content.post_type = 'carousel';
if (!Array.isArray(content.hashtags)) content.hashtags = [];
if (!content.source) content.source = 'Vedic Tradition';
if (!content.theme) content.theme = content.title || 'Vedic Teaching';

// Normalize slides
const roles = ['OPENING', 'RISING', 'TURNING', 'CLIMAX', 'RESOLUTION'];
let slides = content.slides || content.image_prompts || [];
if (!Array.isArray(slides)) slides = [];

slides = slides.map((s, idx) => {
  if (typeof s === 'string') s = { scene: s };
  const narration = s.narration || s.overlay_text || s.sub_text || '';
  let lines = Array.isArray(s.narration_lines) ? s.narration_lines.filter(Boolean) : [];
  if (lines.length === 0 && narration) {
    // fallback: greedy wrap to <=42 chars over 3 lines
    const words = narration.split(/\s+/); lines = []; let cur = '';
    for (const w of words) {
      if ((cur + ' ' + w).trim().length > 42) { lines.push(cur.trim()); cur = w; }
      else { cur = (cur + ' ' + w).trim(); }
    }
    if (cur) lines.push(cur.trim());
    lines = lines.slice(0, 3);
  }
  return {
    slide_number: idx + 1,
    narrative_role: s.narrative_role || roles[idx] || 'RISING',
    narration: narration,
    narration_lines: lines,
    palette: s.palette || '',
    light_source: s.light_source || '',
    scene: s.scene || 'Vedic sacred scene with divine light'
  };
});

while (slides.length < 3) {
  slides.push({ narrative_role: roles[slides.length] || 'CONTEXT', scene: 'Vedic sacred scene', narration: '' });
}
if (slides.length > 5) slides = slides.slice(0, 5);

content.slides = slides;
content.characters = content.characters || {};

// Validate job IDs
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const validIds = (Array.isArray(jobIds) ? jobIds : []).filter(id => UUID_RE.test(id));

if (validIds.length === 0) {
  throw new Error('No valid job IDs found. Raw output: ' + resultText.slice(0, 500));
}

return [{ json: { ...content, job_ids: validIds } }];"""

# Wire Parse Pipeline Output → Wait for Image Generation (skip removed nodes)
wf['connections']['Parse Pipeline Output'] = {
    "main": [[{"node": "Wait for Image Generation", "type": "main", "index": 0}]]
}


# ============================================================
# 5. UPDATE Write Job IDs File — poll with retry logic
# ============================================================
wjid_node = next(n for n in wf['nodes'] if n['name'] == 'Write Job IDs File')

wjid_node['parameters']['jsCode'] = r"""const ids = $json.job_ids || [];
const pollText = `Check status of these Higgsfield image generation jobs using get_generation_status tool for EACH job ID.

Job IDs: ${JSON.stringify(ids)}

POLLING PROCEDURE:
1. Call get_generation_status for EACH job ID
2. If ALL jobs show completed status with image URLs, proceed to step 4
3. If ANY job is still in_progress or pending, call get_generation_status again for the incomplete jobs. Repeat up to 10 times.
4. Return ONLY a JSON array of the completed image URLs in the SAME ORDER as the job IDs above:
["https://url1","https://url2",...]

If a job fails after all retries, include "FAILED" as a placeholder in that position.
Do NOT return anything other than the JSON array. No markdown. No explanations.`;

require('fs').writeFileSync('/tmp/n8n_job_ids.txt', pollText);
return [$input.first()];"""


# ============================================================
# 6. UPDATE Poll Images via CLI — same but ensure 600s timeout
# ============================================================
poll_node = next(n for n in wf['nodes'] if n['name'] == 'Poll Images via CLI')

poll_node['parameters']['jsCode'] = r"""const { execSync } = require('child_process');
try {
  const stdout = execSync(
    'cat /tmp/n8n_job_ids.txt | CLAUDE_CONFIG_DIR=/home/node/.n8n/.claude HOME=/home/node NO_COLOR=1 /usr/local/bin/claude --output-format json',
    { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024, timeout: 600000 }
  );
  return [{ json: { stdout } }];
} catch(e) {
  throw new Error('CLI poll failed: ' + (e.stderr || e.stdout || e.message).slice(0, 2000));
}"""


# ============================================================
# 7. UPDATE Extract URLs & Build Carousel → Validate & Process Images
#    Validates URLs, downloads images, overlays text, uploads to imgbb
# ============================================================
extract_node = next(n for n in wf['nodes'] if n['name'] == 'Extract URLs & Build Carousel')
extract_node['name'] = 'Validate & Process Images'

# Update connections (source side)
for src in list(wf['connections'].keys()):
    if src == 'Extract URLs & Build Carousel':
        wf['connections']['Validate & Process Images'] = wf['connections'].pop(src)
    else:
        for conn_type in wf['connections'][src]:
            for tl in wf['connections'][src][conn_type]:
                for t in tl:
                    if t['node'] == 'Extract URLs & Build Carousel':
                        t['node'] = 'Validate & Process Images'

extract_node['parameters']['jsCode'] = r"""const { execSync } = require('child_process');

// --- 1. Extract image URLs from poll output ---
const raw = $input.first().json.stdout || '';
const cliOut = JSON.parse(raw);
const output = cliOut.result || '';

let rawParsed;
const jsonMatch = output.match(/\[[\s\S]*?\]/);
if (jsonMatch) {
  try { rawParsed = JSON.parse(jsonMatch[0]); } catch(e) {}
}
if (!rawParsed || rawParsed.length === 0) {
  rawParsed = output.split(/(?=https?:\/\/)/).map(p => p.trim())
    .filter(p => p.startsWith('http'))
    .map(p => p.replace(/["'\)\]\[\s,]+$/, ''));
}
if (!rawParsed || rawParsed.length === 0) {
  throw new Error('No image URLs found. Raw: ' + output.slice(0, 500));
}

const failedCount = rawParsed.filter(u => !u || !u.startsWith('http')).length;
if (failedCount > 0) {
  throw new Error(`${failedCount} of ${rawParsed.length} images failed. Aborting.`);
}
const imageUrls = rawParsed;

// --- 2. Get config ---
const ctx = $('Parse Pipeline Output').first().json;
const igConfig = $('Instagram Config').first().json;
const imgbbKey = igConfig.imgbb_api_key || '';
const slides = ctx.slides || [];
const storyTitle = (ctx.title || 'UNTITLED').toUpperCase();

// --- 3. ImageMagick text compositing function ---
function compositeText(inputFile, outputFile, slideNum) {
  const slide = slides[slideNum - 1] || {};
  const lines = Array.isArray(slide.narration_lines) ? slide.narration_lines : [];
  const narration = slide.narration || '';

  // Get actual image dimensions
  const dims = execSync(`identify -format "%wx%h" "${inputFile}"`).toString().trim().split('x');
  const W = parseInt(dims[0]);
  const H = parseInt(dims[1]);

  // Typography constants (% of image dimensions)
  const LM = Math.round(W * 0.06);           // 6% left margin
  const NARR_PT = Math.round(H * 0.022);     // 2.2% narration font size
  const NARR_LH = Math.round(NARR_PT * 1.5); // 150% line height
  const BASELINE_Y = Math.round(H * 0.92);   // 92% from top
  const TITLE_PT = Math.round(H * 0.038);    // 3.8% title font size
  const FADE_START = Math.round(H * 0.52);   // fade starts at 52%
  const FADE_H = H - FADE_START;

  // Narration lines — use pre-broken lines or fallback wrap
  let textLines = lines.slice(0, 3);
  if (textLines.length === 0 && narration) {
    const words = narration.split(/\s+/);
    let cur = '';
    textLines = [];
    for (const w of words) {
      if ((cur + ' ' + w).trim().length > 42) { textLines.push(cur.trim()); cur = w; }
      else { cur = (cur + ' ' + w).trim(); }
    }
    if (cur) textLines.push(cur.trim());
    textLines = textLines.slice(0, 3);
  }

  // Step 1: Create transparent→dark gradient overlay
  const fadeFile = `/tmp/fade_${slideNum}.png`;
  execSync(`convert -size ${W}x${FADE_H} gradient:"rgba(26,26,26,0)-rgba(26,26,26,153)" "${fadeFile}"`);

  // Step 2: Composite gradient onto image
  const withFade = `/tmp/slide_${slideNum}_faded.png`;
  execSync(`convert "${inputFile}" "${fadeFile}" -geometry +0+${FADE_START} -composite "${withFade}"`);

  // Step 3: Add narration text (bottom-up from baseline)
  let cmd = `convert "${withFade}"`;

  const narrFont = '/usr/share/fonts/custom/DMSans-Regular.ttf';
  cmd += ` -font "${narrFont}" -pointsize ${NARR_PT}`;
  cmd += ` -fill "rgba(242,235,217,0.92)"`;
  cmd += ` -kerning 0.5`;

  // Render narration lines bottom-up
  for (let li = textLines.length - 1; li >= 0; li--) {
    const lineIdx = textLines.length - 1 - li;
    const yPos = BASELINE_Y - (lineIdx * NARR_LH);
    const escaped = textLines[li].replace(/"/g, '\\"').replace(/'/g, "'\\''");
    cmd += ` -annotate +${LM}+${yPos} "${escaped}"`;
  }

  // Step 4: Hero title on slide 1 only
  if (slideNum === 1) {
    const topNarrY = BASELINE_Y - ((textLines.length - 1) * NARR_LH);
    const gap = NARR_PT;
    const titleY = topNarrY - gap - Math.round(TITLE_PT * 0.3);
    const titleFont = '/usr/share/fonts/custom/CormorantGaramond-Bold.ttf';
    const titleEscaped = storyTitle.replace(/"/g, '\\"');
    cmd += ` -font "${titleFont}" -pointsize ${TITLE_PT}`;
    cmd += ` -fill "#F2EBD9"`;
    cmd += ` -kerning ${Math.round(TITLE_PT * 0.12)}`;
    cmd += ` -annotate +${LM}+${titleY} "${titleEscaped}"`;
  }

  cmd += ` "${outputFile}"`;
  execSync(cmd);

  // Cleanup temp files
  try { execSync(`rm -f "${fadeFile}" "${withFade}"`); } catch(e) {}
}

// --- 4. Process each image: download → composite text → upload ---
const finalUrls = [];

for (let i = 0; i < imageUrls.length; i++) {
  const url = imageUrls[i];
  const slideNum = i + 1;
  const inputFile = `/tmp/slide_${slideNum}_raw.png`;
  const outputFile = `/tmp/slide_${slideNum}_final.png`;

  try {
    execSync(`curl -s -L -o "${inputFile}" --max-time 30 "${url}"`, { encoding: 'utf8' });

    // Composite text overlay via ImageMagick
    compositeText(inputFile, outputFile, slideNum);

    if (!imgbbKey) {
      finalUrls.push(url);
      continue;
    }

    const imgbbResult = execSync(
      `curl -s -X POST "https://api.imgbb.com/1/upload" -F "key=${imgbbKey}" -F "image=@${outputFile}"`,
      { encoding: 'utf8', timeout: 30000 }
    );
    const imgbbJson = JSON.parse(imgbbResult);
    if (imgbbJson.data && imgbbJson.data.url) {
      finalUrls.push(imgbbJson.data.url);
    } else {
      finalUrls.push(url);
    }
  } catch(e) {
    finalUrls.push(url);
  }
}

// --- 5. Build carousel output ---
const hashtagStr = Array.isArray(ctx.hashtags)
  ? ctx.hashtags.map(h => '#' + String(h).replace(/^#/, '')).join(' ')
  : '';
const fullCaption = (ctx.caption || '') + (hashtagStr ? '\n\n' + hashtagStr : '');

return [{ json: {
  post_type: 'carousel',
  caption: fullCaption.slice(0, 2200),
  image_urls: finalUrls,
  title: ctx.title || '',
  theme: ctx.theme || '',
  source: ctx.source || ''
} }];"""


# ============================================================
# 8. UPDATE Aggregate Carousel Item IDs — reference new node name
# ============================================================
agg_node = next(n for n in wf['nodes'] if n['name'] == 'Aggregate Carousel Item IDs')
agg_node['parameters']['jsCode'] = r"""const items = $input.all();
const ids = items.map(i => i.json.id).filter(Boolean);
if (ids.length < 2) throw new Error('Carousel needs 2+ container IDs, got ' + ids.length);
const carousel = $('Validate & Process Images').first().json;
return [{ json: { children: ids.join(','), caption: carousel.caption } }];"""


# ============================================================
# 9. Instagram Config — add imgbb API key
# ============================================================
ig_node = next(n for n in wf['nodes'] if n['name'] == 'Instagram Config')
ig_obj = json.loads(ig_node['parameters']['jsonOutput'])
ig_obj['imgbb_api_key'] = '432688a051897d9c333c761d48c60a9e'
ig_node['parameters']['jsonOutput'] = json.dumps(ig_obj)


# ============================================================
# 10. UPDATE Log nodes — reference new node names
# ============================================================
for log_name in ['Log Single Post', 'Log Carousel Post']:
    log_nodes = [n for n in wf['nodes'] if n['name'] == log_name]
    if log_nodes:
        code = log_nodes[0]['parameters']['jsCode']
        code = code.replace("$('Extract URLs & Build Carousel')", "$('Validate & Process Images')")
        code = code.replace("$('Parse Content Plan')", "$('Parse Pipeline Output')")
        log_nodes[0]['parameters']['jsCode'] = code


# ============================================================
# 11. FIX Single Image posting nodes — reference new node names
# ============================================================
for n in wf['nodes']:
    if 'parameters' in n:
        for key in ['url', 'body']:
            param_val = n['parameters'].get(key, '')
            if isinstance(param_val, str):
                param_val = param_val.replace("Extract URLs & Build Carousel", "Validate & Process Images")
                param_val = param_val.replace("Parse Content Plan", "Parse Pipeline Output")
                n['parameters'][key] = param_val
        # Also check nested body parameters
        body = n['parameters'].get('body', {})
        if isinstance(body, dict):
            for bkey, bval in body.items():
                if isinstance(bval, dict):
                    params = bval.get('parameters', [])
                    if isinstance(params, list):
                        for p in params:
                            if isinstance(p.get('value', ''), str):
                                p['value'] = p['value'].replace("Extract URLs & Build Carousel", "Validate & Process Images")
                                p['value'] = p['value'].replace("Parse Content Plan", "Parse Pipeline Output")


# ============================================================
# SAVE
# ============================================================
output_path = '/Users/ashwin/Downloads/Veda Katha Reloaded v3.json'
with open(output_path, 'w') as f:
    json.dump(wf, f, indent=2)

# Verify
print(f'Written: {output_path}')
print(f'Total nodes: {len(wf["nodes"])}')
print(f'Total connections: {len(wf["connections"])}')
print()

# Print pipeline chain
print('Pipeline chain:')
visited = set()
def trace(node_name, depth=0):
    if node_name in visited:
        return
    visited.add(node_name)
    print('  ' * depth + node_name)
    conns = wf['connections'].get(node_name, {}).get('main', [[]])
    for tl in conns:
        for t in tl:
            trace(t['node'], depth + 1)

for trigger in ['Manual Trigger', 'Twice Daily 6AM & 6PM IST', 'Webhook Trigger']:
    if trigger in wf['connections']:
        print(f'\n--- {trigger} ---')
        visited = set()
        trace(trigger)

# Verify no dangling references to removed nodes
print('\n--- Checking for dangling references ---')
node_names = {n['name'] for n in wf['nodes']}
for src, conns in wf['connections'].items():
    if src not in node_names:
        print(f'WARNING: Connection source "{src}" not in nodes!')
    for conn_type, tls in conns.items():
        for tl in tls:
            for t in tl:
                if t['node'] not in node_names:
                    print(f'WARNING: Connection target "{t["node"]}" not in nodes!')

# Check jsCode references
print('\n--- Checking node references in code ---')
for n in wf['nodes']:
    code = n.get('parameters', {}).get('jsCode', '')
    for removed in REMOVE_NODES:
        if removed in code:
            print(f'WARNING: "{n["name"]}" still references removed node "{removed}"')
    # Also check for old names
    for old_name in ['Build Content Prompt', 'Generate Content via CLI', 'Parse Content Plan', 'Extract URLs & Build Carousel']:
        if f"$('{old_name}')" in code:
            print(f'WARNING: "{n["name"]}" uses old reference "$(\'{ old_name }\')"')

print('\nDone.')
