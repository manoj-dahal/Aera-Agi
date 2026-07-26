# AERA — Requirements

**Artificial Voice Reasoning Assistant.** A native desktop AI operating
system: persistent memory, an agent roster, a voice with real emotional
expression, and a holographic avatar.

This file records what AERA is required to do, what is built, and what is not.
It is deliberately not a wish list. Every number in it is measured from the
running system, and the ones that can drift are asserted by
`tests/test_documentation.py`, so a claim here cannot quietly stop being true.

The `docs/*.md` set is the original **design specification** — what was
envisaged. This file is the **conformance record** — what exists. Where the two
disagree, this file is correct and the design document is aspirational.

---

## 1. How to read the status column

| Mark | Meaning |
|---|---|
| ✅ | Built, tested, and verified by running it |
| 🟡 | Built with a stated limit — read the note, the limit is real |
| ⬜ | Not built. Refused explicitly at the point of use, never a silent no-op |

A ⬜ item is never faked. Where a capability is missing, the call that would
have used it says so — see §9.

---

## 2. Binding requirements from the user

These come from `docs/ui-page/conversation.txt` and later corrections. They
override the design documents where they conflict, and each is guarded by a
test in `tests/test_requirements.py`.

| # | Requirement | Status | Where |
|---|---|---|---|
| R1 | Settings has exactly three sections: AI, Voice, System | ✅ | `interface/src/pages/settings/SettingsHome.tsx` |
| R2 | Plugins live in Apps, not Settings | ✅ | `interface/src/pages/apps/` |
| R3 | Tap-to-speak triggers the tap-to-memory workflow first | ✅ | `aera/agents/tap_memory.py` |
| R4 | Drag-and-drop targets the transcript panel, not the phone page | ✅ | `interface/src/pages/dashboard/` |
| R5 | The local-LLM button is hidden entirely when none is running | ✅ | `interface/src/pages/models/` |
| R6 | One memory graph; short and long term in a single side panel | ✅ | `aera/memory/`, `interface/src/pages/memory/` |
| R7 | An ethical-hacking agent exists, authorised defensive work only | ✅ | `aera/agents/extended_agents.py` |
| R8 | Terminal-like default tools, with Git enabled by default | ✅ | `aera/skills/registry.py` |
| R9 | The three-dot menu carries update options | ✅ | `interface/src/components/` |
| R10 | Avatar variants are named `anime-g` and `anime-b` | ✅ | `aera/voice/personas.py` |
| R11 | Voice must be multi-language | ✅ | 35 packs — §5 |
| R12 | Voice must express the lyrics and rhythm of a song | ✅ | `aera/voice/music.py` — §6 |

---

## 3. System requirements

### Runtime

| Requirement | Value |
|---|---|
| Python | 3.11 or newer |
| Node | 20 or newer (interface build only) |
| Operating system | Linux, macOS, Windows |
| Memory | 512 MB idle; more with a local model loaded |
| Network | Not required. Every core capability runs offline |

### Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,desktop]"
cd interface && npm install && npm run build
```

### Optional extras

| Extra | Enables | Without it |
|---|---|---|
| `pip install -e ".[voice]"` | Piper neural TTS | Falls back to the bundled formant synthesiser, and says so |
| `espeak-ng` on PATH | System TTS fallback | Same fallback |
| Ollama running locally | Local LLM inference | Cloud providers, or the built-in responder |
| Docker socket readable | Container management | The Docker page reports the socket is unavailable |

---

## 4. Functional requirements

### 4.1 Memory

| Requirement | Status | Note |
|---|---|---|
| Persistent across restarts | ✅ | SQLite-backed graph |
| One graph, short and long term | ✅ | `recent()` reads the short-term ring by design |
| Semantic search | ✅ | 256-dimension `HashingEmbedder` |
| Graph traversal and ranking | ✅ | `graph.find()` |
| Shared between all agents | ✅ | Verified: all 31 enabled agents hold one engine object |

### 4.2 Agents

| Requirement | Status | Note |
|---|---|---|
| Agent roster with intent routing | ✅ | **34 implemented, 31 enabled by default** |
| Risky agents off by default | ✅ | `terminal`, `web` and `audio` are opt-in |
| Skills catalogue | ✅ | 139 skills, 101 available offline |
| Ethical-hacking agent, defensive scope only | ✅ | Refuses unauthorised targets |
| Every agent documented | ✅ | `docs/07-AGENTS.md` roster is generated from the classes and asserted |
| Gallery agent | ⬜ | Never written. The design note is marked so, and media work is split between `vision`, `ocr` and `document` |
| Vision — local analysis | ✅ | Offline: dimensions, palette, brightness, contrast, sharpness, photograph vs screenshot. Needs no model |
| Vision — model description | 🟡 | Multimodal transport works for OpenAI, Anthropic and Gemini. Needs a vision-capable provider configured; without one the measurements are returned and the gap is stated |
| Vision — object recognition offline | ⬜ | Measurement is not recognition. Local analysis never names what is depicted, and says so in its payload |

The three that ship off do so because each can act outside the process:

| Agent | Why | To enable |
|---|---|---|
| `terminal` | Executes shell commands | `agents.terminal`, `security.allow_terminal`, plus an allowlist |
| `web` | Makes outbound requests | `agents.web` and `security.allow_network` |
| `audio` | Needs a speech-to-text engine that is not bundled | `agents.audio` |

### 4.3 Voice — see §5 and §6 for detail

### 4.3a Vision

| Requirement | Status | Note |
|---|---|---|
| Read an image offline | ✅ | `POST /api/v1/vision/analyse` |
| Classify photograph vs screenshot vs graphic | ✅ | Flatness plus saturation and edge energy |
| Report image quality problems | ✅ | Blur, under/over-exposure, flat contrast, too small |
| Send an image to a vision model | ✅ | OpenAI data URL, Anthropic `source.media_type`, Gemini `inline_data.mime_type` |
| Estimate what an image costs to send | ✅ | `POST /api/v1/vision/estimate` |
| Name objects without a model | ⬜ | Not possible from pixels alone; never claimed |

### 4.3b Voice

| Requirement | Status | Note |
|---|---|---|
| Speech-to-text | 🟡 | Pipeline complete; the bundled backend accepts pre-transcribed text. No Whisper adapter yet |
| Text-to-speech | 🟡 | Piper and system TTS supported. Without a model, a formant vocoder that does not articulate words |
| Emotional expression | ✅ | 9 emotions, mood that persists and decays, per-emotion acoustics |
| Multi-language | ✅ | 35 language packs |
| Lip-sync visemes | ✅ | 9 writing systems articulated, 7 timing-only |
| Singing | ✅ | Note plan from lyrics; not audio |

### 4.4 Interface

| Requirement | Status | Note |
|---|---|---|
| React is the only UI | ✅ | The vanilla HTML/CSS/JS UI was deleted |
| Desktop shell | 🟡 | Window and bridge complete; binaries never linked here — §9 |
| Dashboard, memory, agents, workspace, settings pages | ✅ | 294 frontend tests |

### 4.5 API

| Requirement | Value |
|---|---|
| REST operations | **132** |
| Voice endpoints | **18** |
| Transport | HTTP plus a WebSocket gateway |
| Response envelope | Consistent `{success, data, message}` |

---

## 5. Language requirements

**35 packs.** A pack supplies emotion cues, negations, intensifiers, hedges,
clause breaks, number words and unit names. The analysis machinery around them
is language-independent.

Europe and the Americas — `en` `es` `fr` `de` `it` `pt` `nl` `sv` `pl` `ru`
`uk` `el` `tr`

South Asia — `hi` `ne` `mr` `bn` `gu` `pa` `ta` `te` `kn` `ml` `si` `ur`

Middle East — `ar` `he` `fa`

East and South-East Asia, Africa — `ja` `zh` `ko` `th` `vi` `id` `sw`

### 5.1 Numbers must follow each language's own grammar

Not English word order in translated words. This is a hard requirement because
the failure is not subtle: *"achtzig sieben"* is not German, it is nothing.

| Rule | Languages | 87 reads as |
|---|---|---|
| Tens first | English, Spanish, Greek, Turkish… | `eighty seven`, `ochenta y siete` |
| Ones first | German, Dutch, Arabic | `siebenundachtzig`, `سبعة وثمانون` |
| Fully decimal | Chinese | `八十七` |
| All 100 listed | French, Hindi, Nepali | `quatre-vingt-sept`, `सत्तासी`, `सतासी` |
| Irregular, not carried | 10 Indic packs | numerals kept — see below |

Indic languages group by **lakh** (10⁵) and **crore** (10⁷), not by thousand,
so 2,500,000 reads `पच्चीस लाख`.

### 5.2 Where numbers are deliberately not spelled

**23 of 35 packs spell every integer. 12 do not, on purpose.**

- **Japanese and Korean** — the reading depends on the counter that follows.
  一本 is *ippon*, 一人 is *hitori*, 一つ is *hitotsu*. A lookup table would be
  wrong more often than right.
- **Ten Indic packs** (`bn` `gu` `pa` `mr` `ta` `te` `kn` `ml` `si` `ur`) —
  21–99 are irregular and the tables are not carried here. Bengali 21 is একুশ,
  not "twenty one" in Bengali words.

In both cases the numeral is kept. `GET /api/v1/voice/languages` reports
`spells_all_numbers` per language, so a caller is never guessing.

### 5.3 Right-to-left

`ar` `he` `fa` `ur` are flagged `rtl` in the pack listing.

---

## 6. Singing requirements

Speech prosody cannot be relabelled as song. Sung pitch is quantised to a scale
where spoken pitch glides; sung timing is fixed by the bar where spoken timing
follows stress; the unit is the syllable, not the word.

| Requirement | Status | Note |
|---|---|---|
| Count syllables in every supported script | ✅ | Count is *defined as* the split, so they cannot disagree |
| Split words into singable syllables | ✅ | Latin, Indic, Cyrillic, Greek, Thai, abjad, kana, Hangul, Han |
| Scan metre | ✅ | Iamb, trochee, anapest, dactyl, spondee; "free verse" when nothing repeats |
| Detect rhyme scheme | 🟡 | Spelling-based: catches `fire`/`desire` and `time`/`rhyme`, misses eye-rhymes and `love`/`move` |
| Find verse, chorus, bridge | 🟡 | By repetition and shape. A song with no repeated block honestly has no chorus |
| Place notes on beats and bars | ✅ | 12 scales, 8 tempo marks, simple and compound time |
| Emotion sets key and tempo | ✅ | Sad → 62 bpm natural minor 3/4; excited → 152 bpm major 4/4 |
| Melisma | ✅ | Slow phrases only — an ornament everywhere sounds aimless |
| Render to audio | ⬜ | Returns a note plan. The response says so rather than returning silence |

The melody is **derived, not composed**: it arches, and resolves to the tonic.
What is genuinely correct is what the words determine — how many notes, which
land on strong beats, where the singer breathes, how long it takes.

---

## 7. Lip-sync requirements

| Requirement | Status |
|---|---|
| One mouth shape per sound, not per letter | ✅ |
| Mouth closes during pauses | ✅ |
| Works outside the Latin alphabet | ✅ |

**18 scripts get real articulation:** Latin, Cyrillic, Greek, Arabic, Hebrew,
Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada,
Malayalam, Sinhala, Thai, Kana, Hangul.

**8 get syllable timing only** — one jaw opening per character, no articulation:
Han, Georgian, Armenian, Ethiopic, Lao, Khmer, Myanmar, and anything
unrecognised. Han needs a reading dictionary that is not bundled; the rest have
no table yet. `ALPHABETIC` and `TIMING_ONLY` in `aera/voice/scripts.py` say
which, and an import-time check asserts the claim matches the implementation.

---

## 8. Non-functional requirements

| Requirement | Target | Actual |
|---|---|---|
| Python tests pass | all | **2,058 passing, 2 skipped** |
| Frontend tests pass | all | **294 passing** |
| Lint clean | no findings | `ruff check` clean |
| Type-check clean | no errors | `tsc --noEmit` clean |
| Build succeeds | yes | `npm run build` green |
| Core capability offline | yes | No network call on any core path |
| Secrets encrypted at rest | yes | Vault-backed |
| Risky capability opt-in | yes | Terminal, web, audio, Docker control all gated |

---

## 9. Not built — stated, not hidden

Each of these is refused explicitly where it would be used. None returns a
plausible-looking fake.

| Gap | Why | What the system does instead |
|---|---|---|
| **Plugin code execution** | No process isolation. Running untrusted code without a sandbox is not a feature | Manifests validate, permissions gate, execution is refused with the reason |
| **Real speech without a model** | Piper weights are a download; the sandbox that built this cannot reach them | Formant vocoder: correct pitch, pacing and lip-sync, no articulated words. `FORMANT_NOTE` says so wherever audio surfaces |
| **3D avatar model** | Sketchfab and LimeWire are unreachable from the build sandbox | Loader, zip-slip guards and viseme matching are complete. Place a `.glb` or `.zip` at `storage/avatars/anime-g.*` |
| **Whisper STT** | Not yet adapted | `NullSTT` accepts pre-transcribed text so the pipeline is testable end to end |
| **Sung audio** | Needs a real voice model | `POST /voice/sing` returns a note plan and a note saying it is not audio |
| **Phone pairing** | No Device Agent | The phone page reports it |
| ~~Vision / multimodal transport~~ | **Now implemented.** Local analysis runs offline; images are delivered to OpenAI, Anthropic and Gemini in each one's wire format | — |
| **Desktop binaries** | Two independent blockers: this sandbox has no `libpython3.11.so.1.0`, so PyInstaller will not start; and pushing to `.github/workflows/` is rejected without the `workflows` permission, so the build has never run | The workflow is written and its Windows path is asserted by `tests/test_documentation.py::TestDesktopBuildWorkflow`. Move `ci/github-actions-desktop.yml` to `.github/workflows/` to enable it. **No Windows binary exists and none has been launched** |
| **Visual UI verification** | Chromium and Playwright CDNs are blocked | jsdom renders the component tree, not pixels. No screenshot has been taken |

---

## 10. Verification

```bash
# Python: 1,785 tests
.venv/bin/python -m pytest -q

# Lint
.venv/bin/ruff check aera/ tests/ tools/ installer/

# Frontend: 294 tests, type-check, build
cd interface && npm run typecheck && npx vitest run && npm run build
```

The counts in this file are asserted by `tests/test_documentation.py`. If a
language is added, an endpoint changes, or a script gains a reader, that suite
fails until this file is updated — which is the point.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
