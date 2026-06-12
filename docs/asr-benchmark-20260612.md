# ASR Benchmark 2026-06-12

This benchmark compares three local transcription paths on one Chinese video and one English video.
It is a decision aid only; normal provider routing still uses whisper.cpp until model selection is
implemented in the bundle engine.

## Tested Models

- Whisper: `ggml-large-v3-turbo.bin` through local whisper.cpp.
- SenseVoiceSmall: `iic/SenseVoiceSmall` + `fsmn-vad` + `cam++`; no external `ct-punc`, because
  SenseVoiceSmall failed with the punc + speaker combination during the 60 second sample smoke.
- Paraformer-zh: `paraformer-zh` + `fsmn-vad` + `ct-punc` + `cam++`.

## Chinese Source

- URL: `https://b23.tv/eViSC63`
- Source id: `BV1wEVo6eEYv`
- Title: `从凡人到仙人，于谦掉进修仙系统会拿到谁的剧本？【多新鲜呐ep24｜于谦的视频播客】`
- Duration: 2600.4 seconds
- Output directory: `outputs/asr-benchmark-20260612/bilibili_full/`

| Model | Total seconds | RTF | Segments | Initial quality read |
| --- | ---: | ---: | ---: | --- |
| Whisper large-v3-turbo | 1617.34 | 0.622 | 1664 | Fine-grained timing, but slow and has many Chinese proper-noun errors. |
| SenseVoiceSmall | 118.52 | 0.046 | 143 | Very fast and keeps emotion/language tags, but no external punctuation means coarse chunks and more noisy names. |
| Paraformer-zh | 105.47 | 0.041 | 405 | Fastest and most usable Chinese report-input candidate because punctuation and sentence boundaries are better. |

Initial Chinese conclusion: Paraformer-zh is the best next candidate for Chinese local transcription
inside the project. Whisper remains useful as a quality cross-check, but it is too slow on the current
CPU-bound whisper.cpp path for routine long Chinese videos.

## English Source

- URL: `https://youtu.be/AOEr5FrW-lY`
- Source id: `AOEr5FrW-lY`
- Title: `We Were Almost Entirely Wrong About China`
- Duration: 1238.0 seconds
- Output directory: `outputs/asr-benchmark-20260612/youtube_full/`

| Model | Total seconds | RTF | Segments | Initial quality read |
| --- | ---: | ---: | ---: | --- |
| Whisper large-v3-turbo | 802.58 | 0.648 | 340 | Best English accuracy, punctuation, capitalization, and proper nouns. |
| SenseVoiceSmall | 55.64 | 0.045 | 146 | Fast but lower-case, no punctuation, and words can be split across chunks. |
| Paraformer-zh | 63.66 | 0.051 | 158 | Fast but English accuracy is visibly worse, with wrong words and mixed-language noise. |

Initial English conclusion: Whisper large-v3-turbo should remain the English/default-quality path.
Chinese-oriented FunASR models should not be used as the English primary transcript.

## YouTube EJS Note

The YouTube source initially returned only storyboard image formats with `n challenge solving failed`.
Installing `yt-dlp[default]` added `yt-dlp-ejs`, and using `--js-runtimes node` allowed yt-dlp to resolve
real audio/video formats.

## Follow-Up

- Add provider-level model selection before making FunASR part of normal transcription.
- Keep transcript outputs in a common schema with clean text and timestamps.
- If speaker labels are required later, investigate whether FunASR can return reliable diarization fields
  for multi-speaker Chinese podcasts; the current benchmark output did not expose stable speaker labels.
