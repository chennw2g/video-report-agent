from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from video_bundle_agent.bundle.evidence import select_report_evidence
from video_bundle_agent.bundle.readiness import evaluate_bundle_readiness
from video_bundle_agent.bundle.report_input import prepare_report_input
from video_bundle_agent.bundle.transcript_compare import compare_transcripts_for_bundle
from video_bundle_agent.bundle.visual_update import extract_frames_for_bundle
from video_bundle_agent.diagnostics.doctor import run_doctor
from video_bundle_agent.providers import detect_platform
from video_bundle_agent.providers.bilibili.provider import analyze_bilibili
from video_bundle_agent.providers.local_video.provider import analyze_local_video
from video_bundle_agent.providers.xiaohongshu.provider import analyze_xiaohongshu
from video_bundle_agent.providers.youtube.provider import analyze_youtube

app = typer.Typer(no_args_is_help=True, help="Create Codex-readable bundles from video sources.")


@app.command()
def doctor() -> None:
    """Check local tools and print a JSON diagnostics report."""

    report = run_doctor()
    typer.echo(report.model_dump_json(indent=2))


@app.command("check-bundle")
def check_bundle(
    bundle_dir: Annotated[Path, typer.Argument(help="Bundle directory to inspect.")],
) -> None:
    """Check whether a bundle has enough evidence for a substantive report."""

    result = evaluate_bundle_readiness(bundle_dir)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("select-evidence")
def select_evidence(
    bundle_dir: Annotated[Path, typer.Argument(help="Bundle directory to inspect.")],
    max_images: Annotated[
        int,
        typer.Option("--max-images", min=1, help="Maximum screenshots to suggest."),
    ] = 12,
    plan: Annotated[
        Path | None,
        typer.Option(
            "--plan",
            help="Agent-authored visual_selection_plan.json, relative to the bundle by default.",
        ),
    ] = None,
) -> None:
    """Suggest a small set of screenshots and transcript windows for report writing."""

    result = select_report_evidence(bundle_dir, max_images=max_images, plan_path=plan)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("prepare-report")
def prepare_report(
    bundle_dir: Annotated[Path, typer.Argument(help="Existing bundle directory to inspect.")],
    max_images: Annotated[
        int,
        typer.Option("--max-images", min=1, help="Maximum screenshots to include."),
    ] = 12,
    transcript_window_seconds: Annotated[
        float,
        typer.Option(
            "--transcript-window-seconds",
            min=1,
            help="Seconds of transcript context around each selected screenshot.",
        ),
    ] = 20,
    plan: Annotated[
        Path | None,
        typer.Option(
            "--plan",
            help="Agent-authored visual_selection_plan.json, relative to the bundle by default.",
        ),
    ] = None,
    write: Annotated[
        bool,
        typer.Option("--write/--no-write", help="Write report.input.json into the bundle."),
    ] = True,
    draft_content: Annotated[
        bool,
        typer.Option(
            "--draft-content/--no-draft-content",
            help="Write renderer-compatible report.content.draft.json when the bundle is ready.",
        ),
    ] = True,
    full_output: Annotated[
        bool,
        typer.Option(
            "--full-output/--summary",
            help="Print the full report input payload instead of a compact status summary.",
        ),
    ] = False,
) -> None:
    """Prepare a compact report input file from bundle evidence without using an LLM."""

    result = prepare_report_input(
        bundle_dir,
        max_images=max_images,
        transcript_window_seconds=transcript_window_seconds,
        plan_path=plan,
        write=write,
        draft_content=draft_content,
    )
    if full_output or not write:
        output = result
    else:
        selected = result.get("selected_evidence") or {}
        selection = selected.get("selection") or {}
        comparison = result.get("transcript_comparison") or {}
        output = {
            "schema_version": result.get("schema_version"),
            "bundle_dir": result.get("bundle_dir"),
            "report_ready": (result.get("readiness") or {}).get("report_ready"),
            "status": (result.get("readiness") or {}).get("status"),
            "selected_count": selection.get("selected_count"),
            "flagged_transcript_windows": comparison.get("flagged_window_count"),
            "generated_paths": result.get("generated_paths"),
            "limitations": result.get("limitations"),
        }
    typer.echo(json.dumps(output, ensure_ascii=False, indent=2))


@app.command("compare-transcripts")
def compare_transcripts(
    bundle_dir: Annotated[Path, typer.Argument(help="Existing bundle directory to inspect.")],
    window_seconds: Annotated[
        int,
        typer.Option(
            "--window-seconds",
            min=5,
            max=60,
            help="Time window size for transcript comparison.",
        ),
    ] = 15,
) -> None:
    """Compare primary transcript with an alternative transcript when available."""

    result = compare_transcripts_for_bundle(bundle_dir, window_seconds=window_seconds)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("extract-frames")
def extract_frames(
    bundle_dir: Annotated[Path, typer.Argument(help="Existing bundle directory to update.")],
    visual_recall: Annotated[
        str,
        typer.Option(
            "--visual-recall",
            help="Visual recall level for screenshots: low, medium, or high.",
        ),
    ] = "medium",
    visual_strategy: Annotated[
        str,
        typer.Option(
            "--visual-strategy",
            help="Visual extraction strategy: auto, fixed, keyword, scene, or all.",
        ),
    ] = "auto",
    max_screenshots: Annotated[
        int,
        typer.Option(
            "--max-screenshots",
            "--max-candidate-screenshots",
            min=0,
            help="Maximum screenshot candidates to create. Use 0 for no candidate cap.",
        ),
    ] = 0,
) -> None:
    """Extract screenshots from an existing bundle's local working video."""

    if visual_recall not in {"low", "medium", "high"}:
        raise typer.BadParameter("--visual-recall must be one of: low, medium, high.")
    if visual_strategy not in {"auto", "fixed", "keyword", "scene", "all"}:
        raise typer.BadParameter(
            "--visual-strategy must be one of: auto, fixed, keyword, scene, all."
        )

    result = extract_frames_for_bundle(
        bundle_dir,
        visual_recall=visual_recall,
        visual_strategy=visual_strategy,
        max_screenshots=max_screenshots,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def analyze(
    source: Annotated[str, typer.Argument(help="Video URL or local video path.")],
    out: Annotated[Path, typer.Option("--out", "-o", help="Output bundle directory.")],
    comments: Annotated[
        bool,
        typer.Option(
            "--comments/--no-comments",
            help="Fetch audience comments where the provider supports it.",
        ),
    ] = False,
    max_comments: Annotated[
        int,
        typer.Option(
            "--max-comments",
            min=0,
            help="Maximum comments to fetch. Never defaults to all.",
        ),
    ] = 100,
    comment_sort: Annotated[
        str,
        typer.Option("--comment-sort", help="Provider comment sort mode, usually top or new."),
    ] = "top",
    visual_recall: Annotated[
        str,
        typer.Option(
            "--visual-recall",
            help="Visual recall level for screenshots: none, low, medium, or high.",
        ),
    ] = "medium",
    visual_strategy: Annotated[
        str,
        typer.Option(
            "--visual-strategy",
            help=(
                "Visual extraction strategy: auto, fixed, keyword, scene, or all. "
                "Auto keeps medium fast by adding keyword frames but not scene detection."
            ),
        ),
    ] = "auto",
    max_screenshots: Annotated[
        int,
        typer.Option(
            "--max-screenshots",
            "--max-candidate-screenshots",
            min=0,
            help="Maximum screenshot candidates to create. Use 0 for no candidate cap.",
        ),
    ] = 0,
    max_danmaku: Annotated[
        int,
        typer.Option(
            "--max-danmaku",
            min=0,
            help="Maximum Bilibili danmaku items to fetch. Defaults to 0, meaning disabled.",
        ),
    ] = 0,
    force_transcription: Annotated[
        bool,
        typer.Option(
            "--force-transcription/--no-force-transcription",
            help=(
                "Development option: run local audio transcription even if subtitles exist. "
                "Normal runs leave this disabled."
            ),
        ),
    ] = False,
    compare_auto_subtitles: Annotated[
        bool,
        typer.Option(
            "--compare-auto-subtitles/--no-compare-auto-subtitles",
            help=(
                "Run a local whisper.cpp comparison transcript when yt-dlp only "
                "finds automatic subtitles."
            ),
        ),
    ] = True,
    cookies: Annotated[
        Path | None,
        typer.Option(
            "--cookies",
            help="External Netscape cookies file for provider authentication.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    cookies_from_browser: Annotated[
        str | None,
        typer.Option(
            "--cookies-from-browser",
            help="Explicit browser cookie source for yt-dlp, for example: chrome.",
        ),
    ] = None,
    no_llm: Annotated[
        bool,
        typer.Option("--no-llm/--llm", help="Keep analysis to data collection only."),
    ] = True,
) -> None:
    """Analyze a source and write a local bundle. First phase never calls an LLM."""

    if not no_llm:
        raise typer.BadParameter("LLM report generation is not implemented in phase 1.")
    if max_comments < 0:
        raise typer.BadParameter("--max-comments must be zero or greater.")
    if cookies and cookies_from_browser:
        raise typer.BadParameter("Use either --cookies or --cookies-from-browser, not both.")
    if visual_recall not in {"none", "low", "medium", "high"}:
        raise typer.BadParameter("--visual-recall must be one of: none, low, medium, high.")
    if visual_strategy not in {"auto", "fixed", "keyword", "scene", "all"}:
        raise typer.BadParameter(
            "--visual-strategy must be one of: auto, fixed, keyword, scene, all."
        )

    platform = detect_platform(source)
    if platform == "xiaohongshu" and cookies_from_browser:
        raise typer.BadParameter(
            "Xiaohongshu does not support --cookies-from-browser; use --cookies with an "
            "exported Netscape cookies file."
        )
    if platform == "youtube":
        result = analyze_youtube(
            source,
            out,
            fetch_comments=comments,
            max_comments=max_comments,
            comment_sort=comment_sort,
            visual_recall=visual_recall,
            visual_strategy=visual_strategy,
            max_screenshots=max_screenshots,
            force_transcription=force_transcription,
            compare_auto_subtitles=compare_auto_subtitles,
            cookies=cookies,
            cookies_from_browser=cookies_from_browser,
        )
    elif platform == "bilibili":
        result = analyze_bilibili(
            source,
            out,
            fetch_comments=comments,
            max_comments=max_comments,
            comment_sort=comment_sort,
            max_danmaku=max_danmaku,
            visual_recall=visual_recall,
            visual_strategy=visual_strategy,
            max_screenshots=max_screenshots,
            force_transcription=force_transcription,
            cookies=cookies,
            cookies_from_browser=cookies_from_browser,
        )
    elif platform == "xiaohongshu":
        result = analyze_xiaohongshu(
            source,
            out,
            fetch_comments=comments,
            max_comments=max_comments,
            visual_recall=visual_recall,
            visual_strategy=visual_strategy,
            max_screenshots=max_screenshots,
            force_transcription=force_transcription,
            cookies=cookies,
        )
    elif platform == "local_video":
        result = analyze_local_video(source, out)
    else:
        raise typer.BadParameter(f"Unsupported source platform for phase 1: {source}")

    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
