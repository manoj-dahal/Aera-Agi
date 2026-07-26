# 08 - VOICE SYSTEM

Version: 1.0.0

Status: Design Specification. Implementation conformance is recorded in
REQUIREMENTS.md at the repository root; where the two differ, that file
is what was built.

---

# Overview

The Voice System is the primary communication interface between the user and AERA.

Unlike traditional voice assistants, AERA is designed to provide natural, emotionally expressive, low-latency conversations with persistent memory and contextual awareness.

The system combines Speech-to-Text (STT), Large Language Models (LLMs), an Emotion Engine, Text-to-Speech (TTS), and a synchronized Hologram Avatar to create an immersive conversational experience.

---

# Objectives

- Natural Conversations
- Human-like Voice
- Low Latency
- Emotion-Aware Responses
- Persistent Context
- Multi-language Support
- Offline Voice Processing
- Cloud Voice Support

---

# Voice Pipeline

```
User Speech
      │
      ▼
Microphone
      │
      ▼
Voice Activity Detection (VAD)
      │
      ▼
Speech-to-Text
      │
      ▼
Intent Detection
      │
      ▼
Memory Recall
      │
      ▼
AI Core
      │
      ▼
Agent Selection
      │
      ▼
LLM Response
      │
      ▼
Emotion Engine
      │
      ▼
Text-to-Speech
      │
      ▼
Speaker
      │
      ▼
Hologram Lip Sync
```

---

# Main Components

## Speech-to-Text Engine

Converts speech into text.

Responsibilities

- Continuous Listening
- Wake Word Detection
- Noise Reduction
- Language Detection
- Speaker Identification
- Command Recognition

Supported Modes

- Push To Talk
- Continuous Conversation
- Manual Recording
- Wake Word Mode

---

## Conversation Engine

Manages conversations.

Responsibilities

- Context Tracking
- Topic Management
- Multi-turn Dialogue
- Interrupt Handling
- Session Management
- Conversation History

---

## Memory Integration

Every spoken sentence is processed through the Memory Graph.

The system can:

- Recall previous conversations
- Remember project context
- Continue unfinished discussions
- Learn user preferences
- Connect related memories

---

# Emotion Engine

The Emotion Engine determines how AERA speaks and animates.

Voice and avatar always remain synchronized.

Supported emotions include:

- Neutral
- Happy
- Excited
- Calm
- Friendly
- Curious
- Thinking
- Confident
- Surprised
- Empathetic
- Serious
- Focused
- Playful
- Laughing
- Whispering (when appropriate)

The selected emotion influences:

- Voice tone
- Speaking speed
- Pitch
- Facial expression
- Eye movement
- Gesture animation

---

# Natural Speaking Engine

Designed to make speech feel conversational rather than robotic.

Features

- Natural pauses
- Contextual emphasis
- Variable speaking speed
- Smooth sentence transitions
- Reduced repetition
- Emotion-aware pacing

---

# Voice Personality

AERA's voice should sound:

- Friendly
- Intelligent
- Calm
- Professional
- Confident
- Curious
- Respectful
- Expressive

The personality remains consistent while adapting emotional expression to the conversation.

---

# Interrupt Handling

Users may interrupt AERA at any time.

Workflow

```
User Interrupts

↓

Stop Speech

↓

Preserve Context

↓

Listen Immediately

↓

Continue Conversation
```

---

# Voice Commands

Examples

- Open workspace
- Analyze this project
- Search memory
- Open gallery
- Switch AI model
- Explain this code
- Start automation
- Stop speaking

---

# Wake Word (Optional)

Supported modes

- Always Listening
- Push To Talk
- Custom Wake Word
- Disabled

Wake word processing should run locally whenever possible.

---

# Multi-Language Support

**35 language packs are implemented.** A pack supplies emotion cues,
negations, intensifiers, hedges, clause breaks, number words and unit names.
The analysis machinery around them is language-independent.

Europe and the Americas — en es fr de it pt nl sv pl ru uk el tr

South Asia — hi ne mr bn gu pa ta te kn ml si ur

Middle East — ar he fa

East and South-East Asia, Africa — ja zh ko th vi id sw

## Numbers follow each language's own grammar

Not English word order in translated words. German says *siebenundachtzig*,
French *quatre-vingt-sept*, Hindi *सत्तासी*, Chinese *八十七*. Indic languages
group by lakh and crore rather than by thousand.

23 of 35 packs spell every integer. The remaining
12 keep numerals on purpose: Japanese and Korean readings
depend on the counter that follows, and ten Indic packs have irregular 21-99
forms that are not carried here. `GET /api/v1/voice/languages` reports
`spells_all_numbers` per language so a caller is never guessing.

Right-to-left: ar fa he ur.

## Lip-sync across writing systems

18 scripts get real articulation — one mouth shape per sound.
8 get syllable timing only: Han needs a reading dictionary
that is not bundled, and Georgian, Armenian, Ethiopic, Lao, Khmer and Myanmar
have no table yet. `ALPHABETIC` and `TIMING_ONLY` in `aera/voice/scripts.py`
state which, and an import-time check asserts the claim matches the code.

## Not implemented

- Automatic language detection — the language is set, not inferred
- Accent adaptation

---

# Voice Output

Speech synthesis supports:

- Local TTS
- Cloud TTS
- Streaming audio
- High-quality voices
- Low-latency playback

---

# Background Voice Services

The following services run automatically:

- Voice Activity Detection
- Noise Suppression
- Echo Cancellation
- Speech Buffering
- Conversation Context Manager
- Emotion Detection
- Voice Cache
- Audio Streaming
- Memory Synchronization

---

# Hologram Synchronization

During speech, the avatar synchronizes:

- Lip movement
- Eye movement
- Blinking
- Facial expressions
- Head movement
- Hand gestures
- Idle animations

The avatar transitions smoothly between listening, thinking, and speaking states.

---

# Performance Goals

- Voice response latency < 1 second (streaming when possible)
- Natural speech pacing
- Smooth interruption handling
- Low CPU usage during idle listening
- GPU acceleration for avatar rendering

---

# Privacy

Voice data is processed locally whenever supported by the selected components.

User controls include:

- Enable/disable voice history
- Clear voice history
- Microphone permissions
- Local-only mode
- Cloud voice opt-in

---

# Singing

Speech prosody cannot be relabelled as song. Sung pitch is quantised to a
scale where spoken pitch glides; sung timing is fixed by the bar where spoken
timing follows stress; the unit is the syllable, not the word.

`POST /api/v1/voice/sing` returns a note plan: which syllable sounds, at what
pitch, in which bar, for how long. It is derived from the words — syllable
count, stress placement, phrase endings — not composed.

12 scales are available, including bhairav and hijaz, because the
language packs cover South Asia and the Middle East and a major scale would be
the wrong default there. 8 tempo marks from grave to presto.
Simple and compound time signatures.

Emotion picks the key, tempo and time signature: sad is 62 bpm natural minor
in 3/4, excited is 152 bpm major in 4/4.

`POST /api/v1/voice/music/analyse` reads a lyric without setting it — metre,
rhyme scheme, verse and chorus structure, syllable counts.

**This returns a note plan, not audio.** Rendering it needs a real voice
model; the response says so rather than returning silence.

---

# Future Enhancements

Planned improvements

- Voice cloning (user-authorized)
- Emotion recognition from user speech
- Multi-speaker conversations
- Spatial audio
- Personalized speaking style
- Real-time translation during conversations
- Voice biometrics for authentication

---

# Summary

The Voice System provides a natural, context-aware communication layer for AERA. By combining speech recognition, memory, AI reasoning, expressive speech synthesis, and synchronized hologram animation, it creates an intuitive and immersive conversational experience while maintaining user privacy and responsive performance.