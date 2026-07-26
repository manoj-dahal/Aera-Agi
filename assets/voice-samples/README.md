# Voice samples

Two characters, **all nine emotions each**. These are real spoken audio — play
them directly.

The engine has nine emotions and this folder previously covered three, so six
of the nine were undocumented by ear: you could read that `concerned` existed
but never hear what it sounded like.

| Emotion | Anime Girl | Anime Boy | Line |
|---|---|---|---|
| neutral | `anime-g-neutral.mp3` | `anime-b-neutral.mp3` | "Hello! I'm AERA. How can I help you today?" |
| happy | `anime-g-happy.mp3` | `anime-b-happy.mp3` | "Good news! The build is green and every test passed." |
| excited | `anime-g-excited.mp3` | `anime-b-excited.mp3` | "That's amazing! Everything finished perfectly!" |
| calm | `anime-g-calm.mp3` | `anime-b-calm.mp3` | "Everything is steady. Take your time, there's no rush at all." |
| concerned | `anime-g-concerned.mp3` | `anime-b-concerned.mp3` | "Careful — that change looks risky. The database is unstable right now." |
| sad | `anime-g-sad.mp3` | `anime-b-sad.mp3` | "I'm sorry. Unfortunately the deployment failed…" |
| serious | `anime-g-serious.mp3` | `anime-b-serious.mp3` | "This is critical. A security vulnerability was found…" |
| confident | `anime-g-confident.mp3` | `anime-b-confident.mp3` | "Absolutely. I've verified it twice — this will work." |
| curious | `anime-g-curious.mp3` | `anime-b-curious.mp3` | "That's interesting. I wonder what happens if we try it the other way?" |

Every pair speaks the **same line**, so the two characters compare directly:
any difference you hear is the character, not the words.

Both characters are now complete at nine emotions each. `anime-b-confident`
and `anime-b-curious` were blocked by the speech tool's ten-clip-per-turn cap
when the rest were made, and were finished in the following turn.

48 kHz MP3, roughly 1–3 seconds each. All verified distinct by SHA-256 and
checked for a valid MP3 frame header, so none is a truncated or empty file.

## Two different things live here

**The MP3s** were rendered by a neural TTS engine. They are what the characters
should sound like — the reference the runtime is aiming at.

**`acoustics/*.wav`** were produced by AERA's own bundled synthesiser
(`aera.voice.personas`). That is a formant vocoder: it carries each persona's
pitch, pacing, per-emotion acoustics and lip-sync timing, but it does **not**
articulate words. Useful for checking mouth movement lines up; not speech.

Both characters now have all nine there too. The boy's nine were missing
entirely, so the per-emotion acoustic profiles could only be heard in one
voice.

The gap between the MP3s and the WAVs is the honest state of the feature. AERA
can describe a voice precisely and animate to it, but cannot yet *say*
anything, because no pretrained voice model can be downloaded in this
environment — HuggingFace, GitHub release assets and the Piper CDN are all
unreachable. `piper-tts` itself installs from PyPI without trouble; only the
weights are blocked.

## A note on measuring these

The WAVs are dominated by their formants, not their fundamental: "open" uses
F1 = 730 Hz against a 145 Hz fundamental, and brightness scales F1 differently
per persona. A naive Goertzel probe at the persona's pitch therefore reads
formant leakage and can rank the wrong voice higher.

Verified the right way instead — the oscillator's own arithmetic renders the
requested pitch to within 0.05 Hz, and
`tests/test_voice_personas.py::test_the_audio_carries_the_persona_pitch`
measures on a sustained vowel where the fundamental is separable. Anyone
re-checking these by ear or by FFT should know that before concluding the
pitch is wrong.

## Persona parameters

Both voices are defined in `aera/voice/personas.py`:

| | Anime Girl | Anime Boy |
|---|---|---|
| Base pitch | 255 Hz | 145 Hz |
| Excited | 310 Hz, 1.21× speed | 167 Hz, 1.14× speed |
| Sad | 224 Hz, 0.89× speed | 133 Hz, 0.84× speed |
| Brightness | 1.35 | 1.05 |
| Pitch range | 0.24 (expressive) | 0.17 (steadier) |

Both sit above the natural adult averages (roughly 200 Hz female, 120 Hz male)
because anime delivery is performed higher than ordinary speech.

## Getting real speech

Two commands and one download:

```bash
pip install "aera[voice]"                    # installs piper-tts

# Download a voice model plus its config, side by side:
#   https://huggingface.co/rhasspy/piper-voices
#   en/en_US/amy/medium/en_US-amy-medium.onnx
#   en/en_US/amy/medium/en_US-amy-medium.onnx.json
```

Then point AERA at it in `config/voice.yaml`:

```yaml
voice:
  tts_backend: auto          # or piper / system / persona
  piper_model: ~/voices/en_US-amy-medium.onnx
```

`auto` prefers real speech and falls back to the bundled synthesiser, saying
which it chose. Check at any time:

```bash
curl localhost:8080/api/v1/voice/backends
```

```json
{"active": "piper", "synthesises_speech": true,
 "backends": [{"name": "piper", "available": true, "detail": "ready with en_US-amy-medium.onnx"}]}
```

## Other folders

| Folder | What is in it |
|---|---|
| `acoustics/` | 18 formant WAVs — both characters, all nine emotions |
| `casting/` | 8 candidate voices, awaiting a choice |
| `expression/` | Lines demonstrating negation, recovery and prosody |
| `languages/` | Fourteen languages, seven scripts |
| `formant/` | Six earlier WAVs, kept for comparison |

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
