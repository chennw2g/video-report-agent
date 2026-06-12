# Bundle Schema

All JSON files use snake_case field names.

## Output Files

A complete or partial bundle may contain:

```text
bundle.json
metadata.json
transcript.segments.json
transcript.txt
transcript.alternatives.json
transcript.comparison.json
comments.json
danmaku.json
audience_feedback.json
source_chapters.json
media.json
slides.json
content_profile.json
visual_selection_plan.json
report.input.json
report.content.draft.json
screenshots/candidates/*.png
screenshots/selected/*.png
diagnostics.json
manifest.json
```

The tool must not create fake source data. If a provider cannot fetch a source artifact, it should either
omit that artifact path or write an explicitly empty artifact only when the file itself states that nothing
was fetched. The reason must be recorded in `diagnostics.json`.

Normalized files are the core bundle contract. Provider-native files may be stored under `raw/` for debugging,
but report skills should read the normalized artifacts listed in `bundle.json` and `manifest.json` first.

## bundle.json

```json
{
  "schema_version": "0.1.0",
  "source": {
    "platform": "youtube",
    "source_url": "",
    "resolved_url": "",
    "source_id": ""
  },
  "metadata_path": "metadata.json",
  "transcript_path": "transcript.segments.json",
  "transcript_text_path": "transcript.txt",
  "transcript_alternatives_path": "transcript.alternatives.json",
  "transcript_comparison_path": "transcript.comparison.json",
  "comments_path": "comments.json",
  "danmaku_path": null,
  "audience_feedback_path": "audience_feedback.json",
  "source_chapters_path": "source_chapters.json",
  "media_path": "media.json",
  "slides_path": "slides.json",
  "working_video_path": "raw/media/474wZZHoWN4.1080p.webm",
  "working_audio_path": "raw/audio/474wZZHoWN4.webm",
  "content_profile_path": "content_profile.json",
  "diagnostics_path": "diagnostics.json",
  "manifest_path": "manifest.json",
  "capabilities": {
    "has_metadata": true,
    "has_transcript": true,
    "has_comments": true,
    "has_danmaku": false,
    "has_audience_feedback": true,
    "has_slides": true,
    "has_ocr": false
  }
}
```

`working_video_path` and `working_audio_path` are retained local media inputs for staged frame extraction
and audio transcription. Report skills should prefer normalized transcript and slides files over raw media,
but these paths make retry and diagnostics auditable.

`media_path` is optional. Providers such as Xiaohongshu may write `media.json` to record normalized source
video/image URLs and the provider note type before local media files are downloaded.

`source_chapters_path` is optional. When the source platform exposes native chapters, the provider should
write normalized `source_chapters.json` and report skills should prefer it over AI-inferred sections.
For Bilibili, this comes from player `view_points`; `metadata.pages` only records pages/parts and is not the
same as progress-bar chapters. For YouTube, this comes from yt-dlp `chapters` when present. Xiaohongshu
currently has no reliable platform-native chapter source in this project.

## source_chapters.json

`source_chapters.json` records platform-native chapters when available. If the provider successfully checks
the platform and no chapters are returned, it may write an empty `items` list. If the chapter request fails,
omit the bundle path and record diagnostics.

```json
{
  "schema_version": "0.1.0",
  "source": {
    "platform": "bilibili",
    "source_id": "BV...",
    "url": "https://www.bilibili.com/video/BV..."
  },
  "fetched_at": "2026-06-08T00:00:00+00:00",
  "chapter_source": "bilibili_player_v2.view_points",
  "count": 2,
  "items": [
    {
      "id": "chapter_0001",
      "title": "Opening",
      "start": 0.0,
      "end": 42.0,
      "time": "00:00-00:42",
      "thumbnail": "",
      "source": "bilibili_view_points"
    }
  ]
}
```

Known `chapter_source` values:

- `bilibili_player_v2.view_points`
- `yt_dlp.chapters`

## manifest.json

`manifest.json` lists every bundle file and keeps command provenance. `command` is the latest operation that
rewrote the manifest. `command_history` preserves earlier operations, such as the original `analyze` command
followed by `extract_frames` or `compare_transcripts`.

```json
{
  "schema_version": "0.1.0",
  "source": {
    "platform": "youtube",
    "source_url": "",
    "resolved_url": "",
    "source_id": ""
  },
  "files": [],
  "diagnostics_summary": {
    "status": "ok"
  },
  "command": {
    "operation": "extract_frames"
  },
  "command_history": [
    {
      "recorded_at": "2026-06-06T00:00:00+00:00",
      "command": {
        "operation": "analyze",
        "comments": true,
        "max_comments": 100
      }
    },
    {
      "recorded_at": "2026-06-06T00:01:00+00:00",
      "command": {
        "operation": "extract_frames",
        "visual_recall": "low"
      }
    }
  ]
}
```

When platform subtitles are automatic, the bundle may include `transcript.alternatives.json` plus a
`transcript.whisper.segments.json` comparison transcript. The primary `transcript.segments.json` stays the
provider transcript unless subtitles are missing or the run explicitly forces transcription.

`transcript.comparison.json` is a deterministic, non-LLM comparison between the primary transcript and the first
alternative transcript. It aligns transcript text in time windows, records text similarity, highlights technical
term differences, and leaves final judgment to AI.

```json
{
  "schema_version": "0.1.0",
  "primary": {
    "transcript_source": "yt_dlp_auto_subtitle",
    "path": "transcript.segments.json"
  },
  "alternative": {
    "transcript_source": "whisper_cpp",
    "path": "transcript.whisper.segments.json"
  },
  "comparison": {
    "window_seconds": 15,
    "window_count": 8,
    "flagged_window_count": 3
  },
  "items": [
    {
      "start": 30.0,
      "end": 45.0,
      "similarity": 0.81,
      "flagged": true,
      "primary_text": "They have plenty of computer already.",
      "alternative_text": "They have plenty of compute already.",
      "term_differences": {
        "primary_only": ["computer"],
        "alternative_only": ["compute"]
      },
      "word_differences": {
        "primary_only": ["computer"],
        "alternative_only": ["compute"]
      }
    }
  ]
}
```

## visual_selection_plan.json

`visual_selection_plan.json` is authored by the agent in the prep workflow after reading
`content_profile.json`, source chapters, transcript text, and any user focus. It tells the bundle engine what
semantic moments are worth considering for screenshot selection. It is not generated by the bundle engine and
does not replace `slides.json`; it only guides `select-evidence` and `prepare-report`.

The split is intentional: the agent decides what kind of evidence matters, while the Python tool performs
cheap deterministic matching against transcript timestamps and candidate screenshots.

Recommended shape:

```json
{
  "schema_version": "0.1.0",
  "source_type": "tutorial",
  "visual_density": "high",
  "body_screenshot_policy": "selective",
  "semantic_anchors": [
    {
      "id": "anchor_0001",
      "label": "Result screen",
      "terms": ["result", "final output"],
      "time_hints": ["03:20-03:45"],
      "need_screenshot": true,
      "reason": "The result can only be verified visually.",
      "body_placement": "core_points"
    }
  ]
}
```

Rules:

- `body_screenshot_policy` defaults to `selective`: embed body images only when they materially help explain
  the surrounding text.
- `semantic_anchors[].need_screenshot=false` means the anchor may be important for content structure, but
  should not force an image.
- `terms` and `time_hints` are pointers, not final citations. The report skill still reads the transcript
  and selected screenshots before writing claims.
- The tool records the compact plan summary and matched anchor metadata inside
  `report.input.json.selected_evidence`.

## report.input.json

`report.input.json` is generated by `video-bundle-agent prepare-report`. It is a compact bridge for the
AI report skill, not a final report. It contains readiness, metadata summary, content profile, transcript
summary, selected screenshot evidence, nearby transcript windows, flagged transcript-comparison windows,
audience feedback buckets, source chapters, evidence files, and limitations.

It should be generated after AI has written `content_profile.json` and the bundle engine has extracted
screenshots into `slides.json`. The report skill should read this file before writing mode-specific report
content JSON,
but it must still read the full transcript through `transcript.txt` or `transcript.segments.json`.
If `report_ready` is false in the embedded readiness block, the skill should report blockers and repair steps
instead of writing a substantive content report.

```json
{
  "schema_version": "0.1.0",
  "bundle_dir": "outputs/youtube-example",
  "readiness": {
    "report_ready": true
  },
  "metadata": {
    "title": "Example video",
    "duration": 120
  },
  "transcript_comparison": {
    "available": true,
    "flagged_window_count": 2,
    "flagged_windows": []
  },
  "source_chapters": {
    "available": true,
    "path": "source_chapters.json",
    "count": 2,
    "items": []
  },
  "selected_evidence": {
    "selection": {
      "selection_strategy": "plan_guided",
      "body_screenshot_policy": "selective"
    },
    "visual_selection_plan": {
      "available": true,
      "path": "visual_selection_plan.json",
      "semantic_anchor_count": 3
    },
    "selected_images": [
      {
        "path": "screenshots/candidates/000200.0s_fixed.png",
        "selection_reasons": ["semantic_anchor"],
        "anchor_label": "Result screen",
        "anchor_reason": "The result can only be verified visually."
      }
    ]
  },
  "report_contract": {
    "input_path": "report.input.json",
    "draft_content_path": "report.content.draft.json",
    "final_content_paths": {
      "quick": "report.content.quick.json",
      "deep": "report.content.deep.json"
    },
    "html_paths": {
      "quick": "report.zh.quick.html",
      "deep": "report.zh.deep.html"
    },
    "pdf_paths": {
      "quick": "report.zh.quick.pdf",
      "deep": "report.zh.deep.pdf"
    },
    "png_paths": {
      "quick": "report.zh.quick.png",
      "deep": "report.zh.deep.png"
    },
    "compatibility_paths": {
      "content": "report.content.json",
      "html": "report.zh.html",
      "pdf": "report.zh.pdf"
    }
  }
}
```

`report.content.draft.json` is renderer-compatible scaffolding generated only when the bundle is report-ready.
It must be replaced or substantially rewritten by AI before the final report is rendered.

`quick` is the default final report mode. `deep` is used only when the user explicitly requests
`深入分析`, `深度报告`, `详细解读`, or `deep 模式`. Report mode does not affect the bundle or
`report.input.json`; the same prepared bundle can be reused for both modes.

## report.content.<mode>.json

`report.content.quick.json` and `report.content.deep.json` are written by AI, not by the bundle engine.
They should follow `docs/report-output-contract.md`.

Recommended shared shape:

```json
{
  "report_mode": "quick",
  "title": "",
  "eyebrow": "platform · report mode · source type · date",
  "summary": "",
  "conclusion": "",
  "tags": [],
  "metrics": [{"label": "", "value": ""}],
  "evaluation": {
    "scale": {"min": 1, "max": 5},
    "dimensions": [
      {"key": "credibility", "label": "可信度", "score": 0},
      {"key": "originality", "label": "原创性", "score": 0},
      {"key": "value_density", "label": "价值密度", "score": 0},
      {"key": "argument_strength", "label": "论证强度", "score": 0},
      {"key": "information_density", "label": "信息密度", "score": 0},
      {"key": "timeliness", "label": "时效性", "score": 0}
    ],
    "commentary": []
  },
  "visual_evidence": [
    {"image_path": "screenshots/candidates/example.png", "title": "", "caption": ""}
  ],
  "timeline": [
    {"time": "00:00", "topic": "", "summary": "", "evidence": ""}
  ],
  "sections": [{"title": "", "body": [""], "visual_evidence": []}],
  "section_labels": {
    "video_content": "视频内容",
    "codex_analysis": "AI 解读",
    "audience_feedback": "观众反馈",
    "diagnostic_note": "诊断提示"
  },
  "audience_feedback": [
    {
      "title": "",
      "body": [""],
      "representative_comments": [
        {"text": "", "like_count": 0, "reply_count": 0, "source_id": ""}
      ]
    }
  ],
  "diagnostic_notes": [
    {"severity": "warning", "title": "", "body": [""], "evidence": ""}
  ],
  "codex_visuals": [
    {
      "type": "flowchart",
      "title": "",
      "label": "AI 整理",
      "basis": ["transcript:12:34", "screenshots/candidates/example.png"],
      "data": {}
    }
  ],
  "recommendations": [""],
  "attention_notes": [{"severity": "warning", "title": "", "body": [""], "evidence": ""}],
  "project_notes": [""],
  "evidence_files": [{"path": "metadata.json", "purpose": ""}],
  "limitations": []
}
```

The renderer may evolve, but it should follow the Template D / `Editorial Lab` visual baseline in
`docs/report-visual-style.md`. The content contract should preserve these semantics: mode-specific output,
inline visual evidence, AI 1-5 evaluation dimensions, representative comment quotes with `like_count`
when available, and explicit attention notes for source cautions, diagnostics, and report limits.

Source vs AI interpretation:

- Source material and AI interpretation should be distinguishable.
- AI-organized tables, charts, diagrams, risk notes, and evaluation are interpretation, not source claims.
- Render the compact AI multi-dimensional evaluation graphic as the first content module after the top
  basic/source information and before the video overview. Put detailed rating reasoning in a later AI
  critique/detailed evaluation section.
- Use lightweight labels such as `视频内容`, `AI 解读`, `观众反馈`, and `诊断提示` when useful.
- `quick` should not add AI-made charts beyond the fixed multi-dimensional evaluation by default.
- `deep` may include `codex_visuals` such as flowcharts, concept maps, comparison tables, risk/benefit
  matrices, or timelines. They must be labelled `AI 整理` or `AI 解读` and traceable to bundle evidence.

Diagnostic notes:

- `attention_notes` is the preferred final-report module for source cautions, diagnostics, and report
  limits. `diagnostic_notes` may still exist as bundle-engine input, but the renderer should merge it into
  `注意事项`.
- Do not dump raw tool logs in report content.
- Blocking issues should stop substantive report writing and be reported as blockers with repair steps.

Evidence attribution rules:

- `quick` should use lightweight evidence attribution such as timestamps, inline screenshots, comment
  `like_count`, and an evidence-file list.
- `deep` should attribute key claims, disputed judgments, important data, and tutorial steps more explicitly.
- Important conclusions must be traceable to bundle evidence, but not every sentence needs a citation.
- Both modes should keep a final evidence index. `quick` lists key bundle files; `deep` may include used
  screenshots, transcript/comparison files, cited comment files, and relevant diagnostics.

## content_profile.json

`content_profile.json` is authored by AI in the prep skill after reading stage-1 text evidence. It is not a
provider rule output. It records the semantic video type and the selected screenshot policy used by `extract-frames`.

```json
{
  "schema_version": "0.1.0",
  "primary_type": "深度分析",
  "type_tags": ["深度分析", "财经分析"],
  "rationale": "The transcript develops a long-form argument and refers to charts and market data.",
  "visual_policy": {
    "visual_recall": "high",
    "visual_strategy": "all",
    "max_screenshots": 0,
    "reason": "Charts and data-heavy segments need full fixed-interval screenshot coverage."
  }
}
```

`max_screenshots: 0` means no candidate screenshot cap. Use a positive value only when the run
must trade visual completeness for time, disk space, or memory.

## slides.json

`slides.json` indexes screenshots and keyframes. Items may come from fixed-interval extraction,
transcript keyword triggers, scene-change detection, later selected frames, OCR, and scored frames.
The working video should target 1080p video-only input by default, and the actual extracted frame resolution
should be recorded when available. The working video is retained under `raw/media/` by default and may be
listed in `manifest.json` as a raw media artifact.

```json
{
  "source": {
    "platform": "youtube",
    "source_id": "",
    "url": ""
  },
  "video": {
    "path": "raw/media/474wZZHoWN4.1080p.webm",
    "width": 1920,
    "height": 1080,
    "duration": 1729.0,
    "frame_rate": 30.0
  },
  "extraction": {
    "strategy": "mixed",
    "strategies": ["fixed_interval", "keyword_trigger"],
    "visual_strategy": "auto",
    "visual_recall": "medium",
    "interval_seconds": 5,
    "max_screenshots": 0,
    "candidate_cap": null,
    "candidate_cap_unlimited": true,
    "candidate_count": 346,
    "planned_count_before_cap": 390,
    "sampled_due_to_cap": false,
    "skipped_due_to_cap": 0,
    "coverage": {
      "duration": 1729.0,
      "interval_seconds": 5,
      "expected_fixed_interval_count": 346,
      "fixed_interval_coverage_complete": true,
      "candidate_cap_unlimited": true,
      "coverage_truncated": false,
      "first_timestamp": 0.0,
      "last_timestamp": 1725.0
    },
    "fixed_interval": {
      "candidate_count": 346,
      "sampled_due_to_cap": false,
      "skipped_due_to_cap": 0
    },
    "keyword_trigger": {
      "enabled": true,
      "candidate_count": 44,
      "skipped_count": 0
    },
    "scene_change": {
      "enabled": false,
      "status": "not_run",
      "candidate_count": 0,
      "threshold": 0.35
    },
    "ocr_enabled": false,
    "ocr_status": "not_run"
  },
  "items": [
    {
      "id": "slide_0001",
      "timestamp": 12.5,
      "path": "screenshots/candidates/000012.5s_fixed.png",
      "source_reasons": ["fixed_interval", "keyword_trigger"],
      "keyword_matches": ["risk"],
      "trigger_segment_start": 10.4,
      "trigger_text": "Look at this risk chart.",
      "ocr_text": "",
      "ocr_confidence": null,
      "sharpness": null,
      "brightness": null,
      "similarity_hash": null,
      "selected": false
    }
  ]
}
```

If screenshot extraction succeeds:

```json
{
  "slides_path": "slides.json",
  "capabilities": {
    "has_slides": true,
    "has_ocr": false
  }
}
```

If screenshot extraction fails, set `slides_path` to `null`, set `capabilities.has_slides` to `false`,
and record diagnostics.

## media.json

`media.json` records provider-normalized media URLs when the platform exposes video or image assets as part
of a note/post object. It is not a replacement for retained local `working_video_path`, but it makes media
download choices auditable.

```json
{
  "schema_version": "0.1.0",
  "source": {
    "platform": "xiaohongshu",
    "source_url": "",
    "resolved_url": "",
    "source_id": ""
  },
  "fetched_at": "",
  "note_type": "video",
  "video_urls": [],
  "image_urls": []
}
```

## comments.json

```json
{
  "source": {
    "platform": "youtube",
    "source_id": "",
    "url": ""
  },
  "fetched_at": "",
  "count_fetched": 0,
  "total_reported": null,
  "selection": {
    "sort": "like_count_desc",
    "limit": 100,
    "candidate_source": "yt_dlp_write_comments"
  },
  "items": [
    {
      "id": "",
      "parent_id": null,
      "author_name": "",
      "author_id": "",
      "text": "",
      "like_count": 0,
      "reply_count": 0,
      "published_at": "",
      "updated_at": "",
      "is_top_level": true,
      "source": "yt_dlp"
    }
  ],
  "stats": {
    "top_liked": [],
    "top_replied": [],
    "top_terms": [],
    "question_comments": [],
    "critical_comments": [],
    "supportive_comments": []
  }
}
```

`comments.json.items` is ordered by `like_count` descending by default. The provider may use platform
top/hot ordering only to fetch a bounded candidate set; the normalized file records the local selection
rule in `selection.sort`.

Report usage rules:

- `quick` reports should summarize comment evidence briefly and avoid raw comment dumps.
- `deep` reports may cite representative comment viewpoints with short original quotes when useful, but
  each cited comment should include `like_count` when available so the reader can judge visible audience
  approval. Include `reply_count` when discussion intensity matters.
- If `count_fetched` is small or the provider reports partial collection, the report must mark the
  audience-feedback sample as partial.

## diagnostics.json

Common diagnostic codes:

```text
TOOL_MISSING
YTDLP_FAILED
FFMPEG_FAILED
FFPROBE_FAILED
METADATA_UNAVAILABLE
TRANSCRIPT_UNAVAILABLE
TRANSCRIPTION_UNAVAILABLE
AUTO_SUBTITLE_COMPARISON
COMMENTS_UNAVAILABLE
DANMAKU_UNAVAILABLE
BILIBILI_API_UNAVAILABLE
BUNDLE_INCOMPLETE
PLATFORM_UNSUPPORTED
PERMISSION_REQUIRED
COOKIE_REQUIRED
RATE_LIMITED
FRAME_EXTRACTION_FAILED
FFMPEG_NOT_FOUND
VIDEO_FILE_UNAVAILABLE
MEDIA_DOWNLOAD_FAILED
VISUAL_COVERAGE_TRUNCATED
AUDIO_UNAVAILABLE
WHISPER_MODEL_MISSING
OCR_TOOL_MISSING
OCR_FAILED
```

Severity rules:

- metadata failure: `error`
- transcript failure: `warning` or `error`, depending on platform capability
- comments failure: `warning`
- Xiaohongshu interactive verification or account/session risk for comments: `PERMISSION_REQUIRED`
- Xiaohongshu login-expired comment response: `COOKIE_REQUIRED`
- danmaku failure: `warning`
- slides failure: `error` for report-skill readiness, `warning` for non-report diagnostic-only runs
- visual coverage truncation from an explicit positive candidate cap: `warning`
- OCR missing/failure: `warning`, because OCR is optional in phase 1
