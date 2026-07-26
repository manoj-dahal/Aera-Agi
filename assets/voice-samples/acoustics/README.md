# Per-emotion acoustics

Nine renders of the same line, one per emotion, in the `anime-g` voice.

> *"Hello, I am AERA. The deployment has finished."*

| Emotion | Pitch | Jitter | Breath | Tremor | Vibrato | Bright |
|---|---:|---:|---:|---:|---:|---:|
| excited | 310 Hz | 0.009 | 0.04 | 0.030 | 7.0 Hz | 1.22 |
| happy | 286 Hz | 0.006 | 0.05 | 0.015 | 6.2 Hz | 1.12 |
| curious | 276 Hz | 0.005 | 0.07 | 0.010 | 6.0 Hz | 1.10 |
| confident | 261 Hz | 0.002 | 0.03 | 0.000 | 5.0 Hz | 1.05 |
| neutral | 255 Hz | 0.004 | 0.06 | 0.000 | 5.2 Hz | 1.00 |
| calm | 246 Hz | 0.003 | 0.10 | 0.000 | 4.4 Hz | 0.94 |
| concerned | 243 Hz | 0.010 | 0.09 | 0.035 | 5.6 Hz | 0.96 |
| serious | 234 Hz | 0.003 | 0.02 | 0.000 | 4.2 Hz | 0.88 |
| sad | 224 Hz | 0.012 | 0.20 | 0.050 | 3.6 Hz | 0.80 |

## What each dimension does

**Pitch** was previously the only thing that changed, which gave the same
voice transposed rather than a different feeling.

**Jitter** — cycle-to-cycle pitch instability. Distress raises it; certainty
is near-periodic. Confident is the steadiest profile at 0.002, sad the least
at 0.012.

**Breathiness** — aperiodic noise mixed with the tone. This is what makes a
voice sound tired or fragile rather than merely lower. Sad carries six times
the breath of confident.

**Tremor** — slow amplitude shake. Present in distress, absent entirely from
confident and serious, because gravity is controlled rather than wavering.

**Vibrato rate** — 3.6 Hz when low, 7.0 Hz when aroused. Nearly a factor of
two between sad and excited.

**Brightness** — upper-formant gain. Bright reads alert, dark reads withdrawn.

**Harmonic tilt** and **attack** also vary: a tense voice has a stronger
second harmonic, and an urgent one has a sharper onset.

## Verified in the waveform

The profiles are measured in the rendered audio, not just asserted in the
config — `tests/test_voice_personas.py` checks that sad measures noisier and
swings more than confident.

Worth noting one measurement trap. A raw sample-difference metric reported sad
as *smoother* than confident despite three times the breath, because sadness
also darkens the formants and weakens the second harmonic, and those effects
swamp the noise. Measuring the residual after smoothing, relative to signal
level, gives the correct answer: 0.677 for sad against 0.607 for confident.

## The usual caveat

These WAVs come from AERA's bundled formant synthesiser. It carries pitch,
timing, breath and tremor faithfully but does not articulate words — the
acoustic profile is real, the speech is not. See `../README.md`.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
