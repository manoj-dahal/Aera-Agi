# Per-emotion acoustics

Eighteen WAVs: **both characters, all nine emotions**, every pair speaking the
same line. Produced by AERA's own bundled synthesiser, so these are what the
runtime actually generates today — not a reference recording.

The boy's nine were missing entirely before, which meant the per-emotion
acoustic profiles could only be heard in one voice and any per-persona
difference in them was untestable by ear.

## What varies

Pitch and speed alone give a chipmunk-and-slug range: the same voice fast and
high, or slow and low. These profiles also vary how *steady* the voice is, how
much breath is in it, and how bright the timbre sits — the dimensions
phonetics research consistently ties to perceived emotion.

| Emotion | Jitter | Breath | Tremor | Vibrato | Brightness | Attack |
|---|---|---|---|---|---|---|
| excited | 0.009 | 0.04 | 0.03 | 7.0 Hz | 1.22 | 1.5 |
| happy | 0.006 | 0.05 | 0.015 | 6.2 Hz | 1.12 | 1.2 |
| confident | 0.002 | 0.03 | 0.0 | 5.0 Hz | 1.05 | 1.35 |
| curious | 0.005 | 0.07 | 0.01 | 6.0 Hz | 1.10 | 1.1 |
| neutral | 0.004 | 0.06 | 0.0 | 5.2 Hz | 1.00 | 1.0 |
| calm | 0.003 | 0.10 | 0.0 | 4.4 Hz | 0.94 | 0.75 |
| concerned | 0.010 | 0.09 | 0.035 | 5.6 Hz | 0.96 | 1.1 |
| serious | 0.003 | 0.02 | 0.0 | 4.2 Hz | 0.88 | 1.4 |
| sad | 0.012 | 0.20 | 0.05 | 3.6 Hz | 0.80 | 0.55 |

Confident is deliberately the steadiest profile — certainty sounds periodic.
Serious has low breath and no tremor, because gravity is controlled rather
than shaky. Sad is the breathiest by a factor of four.

## These do not articulate words

A formant vocoder carries pitch, pacing and mouth timing. It does not produce
intelligible speech, and nothing here should be mistaken for a voice recording.
See the parent README for how to install a real engine.

## Measuring them

The signal is dominated by its formants: "open" uses F1 = 730 Hz against a
145 Hz fundamental, and brightness scales F1 differently per persona. Probing
energy at the persona's pitch therefore reads formant leakage, and can rank
the wrong voice higher — which it does for four of the nine emotions.

The fundamental is verifiable two ways that do work: the oscillator's own
arithmetic reproduces the requested pitch to within 0.05 Hz, and measuring a
sustained vowel separates the fundamental from the formant, which is what
`tests/test_voice_personas.py` does.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
