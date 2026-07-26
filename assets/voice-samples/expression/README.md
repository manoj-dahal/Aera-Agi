# Expression samples

Six lines showing the emotional range the analyser produces. Real spoken
audio — play them directly.

| File | Emotion | Shows |
|---|---|---|
| `girl-sad-deep.mp3` | sad | Falling pitch, long pauses, slowed delivery |
| `girl-concerned.mp3` | concerned | "not safe" negation caught; urgency preserved |
| `girl-recovery.mp3` | happy | Failure → recovery; the closing clause wins |
| `boy-serious.mp3` | serious | Lowest contour, deliberate pacing |
| `boy-curious.mp3` | curious | Rising terminal pitch on the question |
| `boy-flat.mp3` | *(off)* | Expression disabled — no contour, no mood |

## What the analyser does with these

Run any line through the API to see the reasoning:

```bash
curl -X POST 'localhost:8080/api/v1/voice/analyse?text=Warning:%20it%20is%20not%20safe'
```

```json
{
  "emotion": "concerned",
  "confidence": 0.95,
  "intensity": 0.83,
  "negated": true,
  "reasons": ["concerned in sentence 1"],
  "words": [{"text": "Warning:", "pitch_scale": 0.99, "emphasis": 0.78,
             "pause_after_ms": 240}, "..."],
  "ssml": "<speak><prosody pitch=\"255Hz\">..."
}
```

`/voice/analyse` never moves the standing mood, so auditioning a line is safe.

## Mood

Mood is a baseline that persists between utterances and decays toward neutral
with a four-minute half-life. Three failures in a row leave AERA *subdued*;
after ten minutes of quiet it is *even* again.

```bash
curl localhost:8080/api/v1/voice/mood          # {"valence": -0.32, "label": "subdued"}
curl -X POST localhost:8080/api/v1/voice/mood/reset
curl -X POST 'localhost:8080/api/v1/voice/mood/enabled?enabled=false'
```

With expression off AERA speaks flatly: no detection, no mood, no contour.
That is `boy-flat.mp3`.

## Honest limits

These MP3s were rendered by a neural TTS engine. AERA's own bundled
synthesiser applies the same pitch, timing and pause data but does not
articulate words — see `../README.md`. The analysis layer is real and runs in
the kernel; the *voice* rendering it is not yet bundled, because no pretrained
model can be downloaded in this environment.
