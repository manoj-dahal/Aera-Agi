# Voice casting — pick the two you want

Eight candidates, same line in each so they compare directly:

> *"Hi! I'm AERA, your assistant. Everything is ready — what shall we work on today?"*

## Anime girl

| File | Voice |
|---|---|
| `girl-v1.mp3` | character, index 0 — what shipped previously |
| `girl-v2.mp3` | character, index 1 |
| `girl-v3.mp3` | character, index 2 |
| `girl-v4.mp3` | entertainment, index 0 — different register |

## Anime boy

| File | Voice |
|---|---|
| `boy-v1.mp3` | character, index 0 — what shipped previously |
| `boy-v2.mp3` | character, index 1 |
| `boy-v3.mp3` | character, index 2 |
| `boy-v4.mp3` | entertainment, index 0 — different register |

All eight are verified distinct (SHA-256 compared, no duplicates).

## Once you choose

Tell me which two, and I will regenerate the full emotion set — neutral,
excited, sad, concerned, serious, curious — in those voices, and record the
selection in `aera/voice/personas.py` so the choice is part of the project
rather than a one-off.

## Why these are separate from the runtime

These were rendered by a neural TTS engine. AERA's own bundled synthesiser
applies the matching pitch, pacing and lip-sync timing but does not articulate
words — no pretrained voice model can be downloaded in this environment
(HuggingFace, GitHub release assets and the Piper CDN are all unreachable;
`piper-tts` itself installs from PyPI without trouble).

The persona definitions in `aera/voice/personas.py` are engine-agnostic and
already carry hints for Piper, Coqui and ElevenLabs, so whichever voice you
pick can be reproduced by a real backend once one is installed.
