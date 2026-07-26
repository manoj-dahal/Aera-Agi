# Voice samples

Two characters, three emotions each. **These are real spoken audio** — play
them directly.

| File | Character | Line |
|---|---|---|
| `anime-g-neutral.mp3` | Anime Girl | "Hello! I'm AERA. How can I help you today?" |
| `anime-g-excited.mp3` | Anime Girl | "That's amazing! Everything finished perfectly!" |
| `anime-g-sad.mp3` | Anime Girl | "I'm sorry. Unfortunately the deployment failed…" |
| `anime-b-neutral.mp3` | Anime Boy | "Hello! I'm AERA. How can I help you today?" |
| `anime-b-excited.mp3` | Anime Boy | "That's amazing! Everything finished perfectly!" |
| `anime-b-sad.mp3` | Anime Boy | "I'm sorry. Unfortunately the deployment failed…" |

48 kHz MP3, ~1–2 seconds each.

## Two different things live here

**The MP3s** were rendered by a neural TTS engine. They are what the characters
should sound like — the reference the runtime is aiming at.

**`formant/*.wav`** were produced by AERA's own bundled synthesiser
(`aera.voice.personas`). That is a formant vocoder: it carries each persona's
pitch, pacing and lip-sync timing, but it does **not** articulate words. Useful
for checking mouth movement lines up; not speech.

The gap between the two folders is the honest state of the feature. AERA can
describe a voice precisely and animate to it, but cannot yet *say* anything,
because no pretrained voice model can be downloaded in this environment —
HuggingFace, GitHub release assets and the Piper CDN are all unreachable.
`piper-tts` itself installs from PyPI without trouble; only the weights are
blocked.

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

## Wiring in a real engine

Personas are engine-agnostic — each carries hints for the common backends:

```python
from aera.voice.personas import ANIME_GIRL
ANIME_GIRL.engine_hints["piper"]  # {'voice': 'en_US-amy-medium', 'length_scale': 0.94}
```

Implement `TTSBackend.synthesize` against your engine and pass it in:

```python
from aera.voice.engine import VoiceEngine
kernel.voice = VoiceEngine(config.voice, tts=YourBackend())
```

Pitch, speed and emotion mapping carry over unchanged, and
`/api/v1/voice/personas` will report `synthesises_speech: true` once a real
backend is registered.

## Regenerating the formant set

```bash
python -c "
from pathlib import Path
from aera.voice.personas import ANIME_GIRL, ANIME_BOY, synthesize_wav
from aera.voice.engine import Emotion
for p in (ANIME_GIRL, ANIME_BOY):
    for e in (Emotion.NEUTRAL, Emotion.EXCITED, Emotion.SAD):
        synthesize_wav('Hello! I am AERA.', p, emotion=e,
                       path=Path(f'assets/voice-samples/formant/{p.id}-{e.value}.wav'))
"
```
