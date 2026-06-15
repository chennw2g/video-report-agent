#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install_homebrew=0
install_tools=0
with_funasr=0
with_whisper_cpp=0
with_playwright=0
with_mediacrawler=0
install_plugin=0
skip_doctor=0
tool_root="${VIDEO_BUNDLE_AGENT_TOOL_ROOT:-${VIDEO_REPORT_AGENT_TOOL_ROOT:-$HOME/.local/share/video-report-agent-tools}}"
mediacrawler_path="$project_root/external/MediaCrawler"
whisper_model="large-v3-turbo"
whisper_language_model="base"

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap-macos.sh [options]

Options:
  --install-homebrew        Install Homebrew if missing
  --install-tools           Install Python 3.12, uv, ffmpeg, node, git, and tesseract through Homebrew
  --with-funasr             Install the optional FunASR Python extra
  --with-whisper-cpp        Install whisper-cpp through Homebrew and download model files
  --whisper-model NAME      Main whisper.cpp model. Default: large-v3-turbo
  --whisper-language-model NAME
                            Language probe model. Default: base
  --with-playwright         Install Playwright Chromium
  --with-mediacrawler       Clone/sync MediaCrawler under external/MediaCrawler
  --install-plugin          Install the Codex plugin into ~/plugins and ~/.agents
  --tool-root PATH          External tool/model root. Default: ~/.local/share/video-report-agent-tools
  --mediacrawler-path PATH  MediaCrawler checkout path. Default: ./external/MediaCrawler
  --skip-doctor             Do not run video-bundle-agent doctor at the end
  -h, --help                Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-homebrew)
      install_homebrew=1
      shift
      ;;
    --install-tools)
      install_tools=1
      shift
      ;;
    --with-funasr)
      with_funasr=1
      shift
      ;;
    --with-whisper-cpp)
      with_whisper_cpp=1
      shift
      ;;
    --whisper-model)
      whisper_model="$2"
      shift 2
      ;;
    --whisper-language-model)
      whisper_language_model="$2"
      shift 2
      ;;
    --with-playwright)
      with_playwright=1
      shift
      ;;
    --with-mediacrawler)
      with_mediacrawler=1
      shift
      ;;
    --install-plugin)
      install_plugin=1
      shift
      ;;
    --tool-root)
      tool_root="$2"
      shift 2
      ;;
    --mediacrawler-path)
      mediacrawler_path="$2"
      shift 2
      ;;
    --skip-doctor)
      skip_doctor=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is intended for macOS." >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  if [[ "$install_homebrew" -eq 1 ]]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -x /opt/homebrew/bin/brew ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
      eval "$(/usr/local/bin/brew shellenv)"
    fi
  else
    echo "Homebrew was not found. Install Homebrew or rerun with --install-homebrew." >&2
    exit 1
  fi
fi

if [[ "$install_tools" -eq 1 ]]; then
  brew install python@3.12 uv ffmpeg node git tesseract
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv was not found. Install uv with Homebrew or rerun with --install-tools." >&2
  exit 1
fi

export VIDEO_BUNDLE_AGENT_TOOL_ROOT="$tool_root"
export XHS_MEDIACRAWLER_PATH="$mediacrawler_path"

sync_args=(sync)
if [[ "$with_funasr" -eq 1 ]]; then
  sync_args+=(--extra funasr)
fi

(
  cd "$project_root"
  uv "${sync_args[@]}"
)

if [[ "$with_playwright" -eq 1 ]]; then
  (
    cd "$project_root"
    uv run playwright install chromium
  )
fi

if [[ "$with_whisper_cpp" -eq 1 ]]; then
  bash "$project_root/scripts/install-whisper-cpp-macos.sh" \
    --install-root "$tool_root" \
    --model "$whisper_model" \
    --language-model "$whisper_language_model"
fi

if [[ "$with_mediacrawler" -eq 1 ]]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "git was not found. Install Git or rerun with --install-tools." >&2
    exit 1
  fi
  if [[ ! -f "$mediacrawler_path/main.py" ]]; then
    mkdir -p "$(dirname "$mediacrawler_path")"
    git clone https://github.com/NanmiCoder/MediaCrawler.git "$mediacrawler_path"
  fi
  (
    cd "$mediacrawler_path"
    uv sync
    uv run playwright install chromium
  )
fi

if [[ "$install_plugin" -eq 1 ]]; then
  bash "$project_root/scripts/install-plugin-macos.sh" --project-root "$project_root"
fi

if [[ "$skip_doctor" -eq 0 ]]; then
  (
    cd "$project_root"
    uv run video-bundle-agent doctor
  )
fi

echo
echo "Bootstrap completed."
echo "Project root: $project_root"
echo "Tool root: $tool_root"
echo "MediaCrawler path: $mediacrawler_path"
