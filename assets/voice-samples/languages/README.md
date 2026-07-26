# Multilingual voice

Six languages, real spoken audio.

| File | Language | Line |
|---|---|---|
| `es-girl.mp3` | Español | "¡Hola! Soy AERA. El despliegue ha terminado…" |
| `fr-girl.mp3` | Français | "Bonjour ! Je suis AERA. Désolé, le déploiement a échoué." |
| `de-boy.mp3` | Deutsch | "Hallo! Ich bin AERA. Das ist fantastisch…" |
| `hi-girl.mp3` | हिन्दी | "नमस्ते! मैं AERA हूँ। यह शानदार है…" |
| `ne-girl.mp3` | नेपाली | "नमस्ते! म AERA हुँ। माफ गर्नुहोस्, असफल भयो।" |
| `ja-boy.mp3` | 日本語 | "こんにちは！AERAです。素晴らしい…" |

## What changed in the engine

`language` was threaded through the whole voice pipeline and then ignored.
Every emotion cue, negation word and number was English, so:

- `¡Eso es fantástico!` scored **neutral**
- `87% completado` was read as *"eighty seven percent completado"*

Both are fixed. `aera/voice/languages.py` holds one pack per language —
emotion cues, negations, intensifiers, hedges, clause breaks, number words and
unit names. The analysis machinery is unchanged: clause-scoped negation,
intensifier boosting and recency weighting are language-independent, only the
vocabulary differs.

```bash
curl localhost:8080/api/v1/voice/languages
curl -X POST localhost:8080/api/v1/voice/languages/es
```

## Numbers follow the language

| | 87 | 1200 |
|---|---|---|
| en | eighty seven | one thousand two hundred |
| es | ochenta siete | uno mil dos cien |
| fr | quatre-vingts sept | un mille deux cent |
| de | achtzig sieben | eins tausend zwei hundert |
| ne | असी सात | एक हजार दुई सय |

Hindi and Nepali group by **lakh** and **crore** rather than thousands.

Japanese deliberately leaves digits alone: counters change the reading
depending on what is being counted, and a lookup table cannot capture that. A
wrong reading is worse than a numeral the engine handles correctly itself.

## Scope, stated plainly

Six languages have real packs. Anything else — Portuguese, Arabic, Korean —
still runs, but falls back to English cue matching, which **will** misread
sentiment. The API says which case you are in rather than leaving you to
guess:

```json
{"active": "pt", "supported": false, "fallback": "en"}
```

English-only rules are gated rather than misapplied: `Dr.` is not expanded in
German, and a language without a unit word keeps the symbol instead of
borrowing "percent".

## The usual caveat

These MP3s were rendered by a neural TTS engine. AERA's bundled synthesiser
carries pitch, timing and lip-sync but does not articulate words. Install a
Piper voice for the target language and the same expression analysis drives it
— see `../README.md`.
