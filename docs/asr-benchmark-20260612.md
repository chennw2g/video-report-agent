# ASR Benchmark 2026-06-12

This benchmark compares local transcription paths on one Chinese video and one English video.
It is the basis for the current language-aware local transcription policy: Chinese defaults to FunASR
Paraformer-zh, while English and other non-Chinese languages use whisper.cpp.

Important workflow note: the Bilibili benchmark audio was obtained through an ad hoc same-audio test
path for ASR comparison. It was not a production provider workflow run. Normal Bilibili analysis remains
`bilibili-api-python` primary for metadata/comments/chapters/playurl media, with `yt-dlp` only as fallback.

## Tested Models

- Whisper: `ggml-large-v3-turbo.bin` through local whisper.cpp.
- SenseVoiceSmall: `iic/SenseVoiceSmall` + `fsmn-vad` + `cam++`; no external `ct-punc`, because
  SenseVoiceSmall failed with the punc + speaker combination during the 60 second sample smoke.
- Paraformer-zh: `paraformer-zh` + `fsmn-vad` + `ct-punc` + `cam++`.
- Whisper base follow-up: `ggml-base.bin` through local whisper.cpp, added after the initial run to test
  whether a faster English Whisper model can keep acceptable accuracy.
- Whisper turbo q5_0 follow-up: `ggml-large-v3-turbo-q5_0.bin`, locally quantized from the installed turbo
  model with `whisper-quantize.exe q5_0`.

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

Chinese limitation: this Bilibili video did not provide an authoritative platform subtitle in the benchmark
artifacts, so no true WER can be computed. Reference-free checks are therefore only directional:

- Exact key-term hits after whitespace removal:
  - Whisper large-v3-turbo: 18 terms, 99 total hits.
  - SenseVoiceSmall: 19 terms, 121 total hits.
  - Paraformer-zh: 20 terms, 108 total hits.
- Manual spot windows show all three models preserve the main topic flow, but all make Chinese proper-noun
  and homophone mistakes. Examples:
  - Whisper: `韩丽杰英`, `盗友`, `一见三点`, `红尘节`.
  - SenseVoiceSmall: `修馆修仙界`, `长宁波`, `国唱三维动画`, `三级动画`.
  - Paraformer-zh: `狐仙界`, `韩立杰英`, `长青鹿`, `天子过得`, `红尘节`.
- Current practical read: Paraformer-zh is still the most usable Chinese candidate because punctuation and
  sentence boundaries make report preparation easier, but a future production route should keep a flagged
  comparison path for important proper nouns and domain terms.

## English Source

- URL: `https://youtu.be/AOEr5FrW-lY`
- Source id: `AOEr5FrW-lY`
- Title: `We Were Almost Entirely Wrong About China`
- Duration: 1238.0 seconds
- Output directory: `outputs/asr-benchmark-20260612/youtube_full/`

| Model | Total seconds | RTF | Segments | Initial quality read |
| --- | ---: | ---: | ---: | --- |
| Whisper large-v3-turbo | 802.58 | 0.648 | 340 | Best English accuracy, punctuation, capitalization, and proper nouns. |
| Whisper base | 94.42 | 0.076 | 389 | Much faster than turbo and still close to turbo on this official-caption English test. |
| Whisper large-v3-turbo q5_0 | 977.07 | 0.789 | 357 | Smaller file, but slower than unquantized turbo on the current CPU build. |
| SenseVoiceSmall | 55.64 | 0.045 | 146 | Fast but lower-case, no punctuation, and words can be split across chunks. |
| Paraformer-zh | 63.66 | 0.051 | 158 | Fast but English accuracy is visibly worse, with wrong words and mixed-language noise. |

Initial English conclusion: Whisper large-v3-turbo remains the English/default-quality path. Whisper base is
the leading English speed candidate from the tested local models. Chinese-oriented FunASR models should not
be used as the English primary transcript.

Official-caption comparison:

- Reference file: `outputs/asr-benchmark-20260612/youtube_official.en-US.json3`.
- The official JSON3 subtitle contains HTML styling tags; WER below strips those tags before tokenization.
- Reference length after cleanup: 2,783 English tokens.

| Model | WER vs official subtitle | Suspected token errors | Substitutions | Deletions | Insertions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Whisper large-v3-turbo | 2.01% | 56 | 31 | 1 | 24 |
| Whisper base | 2.23% | 62 | 43 | 9 | 10 |
| Whisper large-v3-turbo q5_0 | 2.44% | 68 | 28 | 3 | 37 |
| SenseVoiceSmall | 11.32% | 315 | 181 | 12 | 122 |
| Paraformer-zh | 21.09% | 587 | 377 | 48 | 162 |

Typical English error patterns:

- Whisper mostly disagrees on names or formatting and sometimes includes neighboring-window words:
  `Sarko`/`Zarco`, `Burgas`/`Burgos`, `km`/`kilometers`.
- Whisper base gives up only a small amount of accuracy on this video while cutting wall time by about 8.5x
  compared with local turbo.
- Whisper turbo q5_0 is not useful on this current CPU-only whisper.cpp build: it reduced model size from
  about 1.6 GB to about 547 MB, but it was slower than unquantized turbo and less accurate than base on this
  English source.
- SenseVoiceSmall is fast but splits words and loses formatting: `we` -> `w e`, `different` -> `diff erent`,
  `country` -> `coun try`, `outcome` -> `ou tcome`.
- Paraformer-zh is not a good English primary model. It shows more real word substitutions and noise:
  `Huawei` -> `Wailway`, `tablets` -> `cablets`, `home automation` -> `home moderation`, plus occasional
  mixed-language artifacts.

## YouTube EJS Note

The YouTube source initially returned only storyboard image formats with `n challenge solving failed`.
Installing `yt-dlp[default]` added `yt-dlp-ejs`, and using `--js-runtimes node` allowed yt-dlp to resolve
real audio/video formats.

The project still detects the standalone `yt-dlp` binary for normal wrapper calls. The Python package was
added because this benchmark encountered two practical issues: the standalone executable had a local
PyInstaller extraction/cache failure during ad hoc use, and current YouTube extraction needed the EJS
solver components available through `yt-dlp[default]`.

## Follow-Up

- Keep provider-level language-aware model selection active: Chinese uses FunASR Paraformer-zh, English and
  other non-Chinese languages use whisper.cpp.
- Use a short audio-probe language detection pass before full local transcription. Platform metadata and
  subtitle language should be fallback hints, because Bilibili, YouTube, and Xiaohongshu can all contain
  cross-language speech independent of title or platform. Low-confidence probe results should also fall back
  to those hints instead of overriding them.
- GPU-enabled whisper.cpp has now been built and tested on 2026-06-14. On this workstation,
  `ggml-large-v3-turbo.bin` completed the English benchmark audio in 38.19 seconds for 1238.04 seconds of
  audio, RTF 0.03085, and WER 1.29% against the YouTube official JSON3 subtitle. Use turbo as the current
  English/default-quality path when the CUDA build is available; keep base as a CPU-only speed fallback.
- Keep transcript outputs in a common schema with clean text and timestamps.
- FunASR `sentence_info[].spk` is now preserved in the benchmark output schema. Treat speaker labels as
  anonymous voice-cluster ids (`0`, `1`, etc.), not real names.
