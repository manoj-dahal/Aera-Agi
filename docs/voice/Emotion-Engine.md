# Emotion Engine

Version: 1.0.0

Status: Stable

---

# Overview

The Emotion Engine determines the emotional tone of every AI response.

It analyzes conversation context, user sentiment, confidence levels, and system events to generate natural emotional expressions for both voice and avatar.

---

# Supported Emotions

The nine the engine implements, matching `Emotion` in
`aera/voice/engine.py`. This list previously named Thinking and Friendly,
which have never existed, and omitted Sad, which does.

- Neutral
- Happy
- Excited
- Curious
- Calm
- Confident
- Concerned
- Serious
- Sad

---

# Pipeline

```
Conversation

↓

Sentiment Analysis

↓

Emotion Selection

↓

Voice Style

↓

Avatar Expression
```

---

# Outputs

- Voice Tone
- Facial Expression
- Speaking Speed
- Pitch
- Gestures

Each emotion carries its own acoustics -- jitter, breathiness, tremor,
vibrato rate and depth, brightness, harmonic tilt and attack -- so the
difference between sad and confident is audible in the waveform rather than
a pitch offset with a label on it. See `EMOTION_ACOUSTICS` in
`aera/voice/personas.py`.

---

# Mood

Emotion is per utterance; mood persists between them. A run of failures
leaves AERA subdued for a while, and one good result does not instantly make
it cheerful. Valence runs -1 to +1 and decays toward neutral with a 240
second half-life.

---

# Nuance

Detection understands negation, intensifiers and hedging, and scopes a
negation to its own clause. "Warning: it is not safe" reads as concerned,
not calm, because the "not" applies to "safe" and not to "warning".

Vocabulary comes from the language pack, so this works in all 35 languages;
the machinery around it is language-independent.

---

# Integration

- Voice Agent
- Avatar
- Core Agent
- Memory Agent

---

# Summary

The Emotion Engine makes AERA sound natural and emotionally appropriate.