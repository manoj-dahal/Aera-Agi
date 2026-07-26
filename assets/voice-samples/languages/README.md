# Multilingual voice

**Fourteen languages, real spoken audio.** Play them directly.

The engine supports 35 language packs; fourteen of them now have a recorded
line. The remaining 21 are listed at the bottom rather than left for you to
work out by subtraction.

| File | Language | Line | Reads as |
|---|---|---|---|
| `es-girl.mp3` | Español | "¡Hola! Soy AERA. El despliegue ha terminado…" | happy |
| `fr-girl.mp3` | Français | "Bonjour ! Je suis AERA. Désolé, le déploiement a échoué." | sad |
| `de-boy.mp3` | Deutsch | "Hallo! Ich bin AERA. Das ist fantastisch…" | excited |
| `it-boy.mp3` | Italiano | "Ciao! Sono AERA. È fantastico, tutto è andato a buon fine." | excited |
| `pt-girl.mp3` | Português | "Olá! Eu sou a AERA. Desculpe, a implantação falhou." | sad |
| `ru-girl.mp3` | Русский | "Привет! Я AERA. Отлично, развёртывание завершено успешно." | excited |
| `hi-girl.mp3` | हिन्दी | "नमस्ते! मैं AERA हूँ। यह शानदार है…" | excited |
| `ne-girl.mp3` | नेपाली | "नमस्ते! म AERA हुँ। माफ गर्नुहोस्, असफल भयो।" | sad |
| `bn-girl.mp3` | বাংলা | "নমস্কার! আমি AERA। দুঃখিত, স্থাপন ব্যর্থ হয়েছে।" | sad |
| `ta-girl.mp3` | தமிழ் | "வணக்கம்! நான் AERA. அருமை, அனைத்தும் வெற்றிகரமாக முடிந்தது." | excited |
| `ar-girl.mp3` | العربية | "مرحبا! أنا AERA. تحذير، قاعدة البيانات غير مستقرة الآن." | concerned |
| `zh-girl.mp3` | 中文 | "你好！我是 AERA。太棒了，部署已经完成，一切正常。" | happy |
| `ja-boy.mp3` | 日本語 | "こんにちは！AERAです。素晴らしい…" | excited |
| `ko-boy.mp3` | 한국어 | "안녕하세요! 저는 AERA입니다. 죄송합니다, 배포가 실패했습니다." | sad |

The "reads as" column is what `ExpressionAnalyser` actually returns for that
line, verified rather than assumed. Seven scripts are represented: Latin,
Cyrillic, Arabic, Devanagari, Bengali, Tamil, Han, Kana and Hangul.

## One result worth explaining

The Chinese line reads **happy**, not excited, even though it contains 太棒了
("fantastic"), which is an excited cue. That is correct arithmetic and a real
limitation at the same time.

`好` is a happy cue, and it appears inside 你好 — "hello". So the line scores
one excited hit and two happy hits, and happy wins on count. Chinese is
written without spaces, so the matcher cannot assert a word boundary and a
one-character cue matches wherever it occurs, including inside an unrelated
word.

This is the same class of problem as the French `bien sûr` / `bien` collision,
which was fixed by preferring the longest match at a position. That fix does
not help here because 好 and 太棒了 are at *different* positions — both really
are present. Shortening the cue list would lose real signal; the honest
description is that single-character cues in unspaced scripts over-trigger.

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

Numbers follow each language's own grammar rather than English word order in
translated words:

| Language | 87 |
|---|---|
| English | eighty seven |
| Spanish | ochenta y siete |
| German | siebenundachtzig |
| French | quatre-vingt-sept |
| Arabic | سبعة وثمانون |
| Hindi | सत्तासी |
| Nepali | सतासी |
| Chinese | 八十七 |

Twelve of the 35 packs deliberately keep numerals. Japanese and Korean
readings depend on the counter that follows — 一本 is *ippon*, 一人 is
*hitori* — and ten Indic packs have irregular 21–99 forms not carried here.
`GET /api/v1/voice/languages` reports `spells_all_numbers` per language so a
caller is never guessing.

## Languages with a pack but no recording yet

`el` `en` `fa` `gu` `he` `id` `kn` `ml` `mr` `nl` `pa` `pl` `si` `sv` `sw`
`te` `th` `tr` `uk` `ur` `vi`

English has no file here because the whole parent folder is English — see
`../README.md` for all nine emotions in both voices.

## These are reference recordings, not AERA speaking

Rendered by a neural TTS engine. AERA's own bundled synthesiser is a formant
vocoder that carries pitch, pacing and lip-sync timing but does not articulate
words. Install a real engine to close the gap:

```bash
pip install "aera[voice]"
```

Piper publishes voices for most of these languages at
`huggingface.co/rhasspy/piper-voices`.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
