# Text To Speech (TTS)

Version: 1.0.0

Status: Implemented, with the bundled-synthesiser limit stated below.

Priority: Critical

---

# Overview

Text-to-Speech converts AI-generated text into natural, expressive speech.

The engine supports multilingual voices, emotion-aware synthesis, streaming audio generation, and low-latency playback.

---

# Architecture

```
AI Response

↓

Emotion Engine

↓

Voice Selection

↓

Speech Synthesis

↓

Audio Output
```

---

# Features

- Emotion Support — nine emotions, each with its own acoustics
- Voice Personalities — anime-g, anime-b and the neutral AERA voice
- Multi-Language — 35 language packs drive normalisation and expression
- Offline — no network call on any synthesis path

## What produces the audio

Three backends, tried in order by `best_available()`:

1. **Piper** — neural, offline, genuinely speaks words. Needs a `.onnx`
   voice model, which is a separate download from
   `huggingface.co/rhasspy/piper-voices`. Install with
   `pip install -e ".[voice]"` and set `voice.piper_model`.
2. **System TTS** — espeak-ng or macOS `say`. Lower quality, usually already
   present. The language is passed through, so Spanish is read with Spanish
   letter-to-sound rules.
3. **Formant synthesiser** — the bundled fallback.

**The bundled fallback does not articulate words.** It is a formant vocoder:
the audio carries the persona's pitch, pacing, emotional acoustics and
lip-sync timing, and it exists so those can be developed and heard without a
downloadable model. It does not produce intelligible speech.
`GET /api/v1/voice/backends` reports `synthesises_speech` so a caller can
tell which of the three is active without inspecting a result.

## Not implemented

- Streaming audio — synthesis returns a complete result
- Voice cloning
- Voice Speed Control
- Pitch Control

---

# Supported Engines

- ElevenLabs
- OpenAI TTS
- Azure Speech
- Google TTS
- Piper
- Coqui TTS

---

# Configuration

```yaml
tts:

  enabled: true

  provider: openai

  voice: alloy

  speed: 1.0

  emotion: true

  streaming: true
```

---

# Controls

- Volume
- Speed
- Pitch
- Emotion
- Voice Selection

---

# Summary

Text-to-Speech gives AERA a natural, expressive speaking voice.