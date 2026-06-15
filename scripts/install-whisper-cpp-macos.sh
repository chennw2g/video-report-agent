#!/usr/bin/env bash
set -euo pipefail

install_root="${VIDEO_BUNDLE_AGENT_TOOL_ROOT:-${VIDEO_REPORT_AGENT_TOOL_ROOT:-$HOME/.local/share/video-report-agent-tools}}"
model="large-v3-turbo"
language_model="base"
skip_runtime=0
skip_model=0
skip_language_model=0
set_shell_env=0
force=0

usage() {
  cat <<'EOF'
Usage: scripts/install-whisper-cpp-macos.sh [options]

Options:
  --install-root PATH       Tool/model root. Default: ~/.local/share/video-report-agent-tools
  --model NAME              Main model name. Default: large-v3-turbo
  --language-model NAME     Language probe model name. Default: base
  --skip-runtime            Do not install Homebrew whisper-cpp
  --skip-model              Do not download the main model
  --skip-language-model     Do not download the language probe model
  --set-shell-env           Append model/tool exports to ~/.zshrc
  --force                   Re-download model files
  -h, --help                Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-root)
      install_root="$2"
      shift 2
      ;;
    --model)
      model="$2"
      shift 2
      ;;
    --language-model)
      language_model="$2"
      shift 2
      ;;
    --skip-runtime)
      skip_runtime=1
      shift
      ;;
    --skip-model)
      skip_model=1
      shift
      ;;
    --skip-language-model)
      skip_language_model=1
      shift
      ;;
    --set-shell-env)
      set_shell_env=1
      shift
      ;;
    --force)
      force=1
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

model_file() {
  local name="$1"
  if [[ "$name" == *.bin ]]; then
    printf '%s\n' "$name"
  elif [[ "$name" == ggml-* ]]; then
    printf '%s.bin\n' "$name"
  else
    printf 'ggml-%s.bin\n' "$name"
  fi
}

download_model() {
  local file="$1"
  local destination="$2"
  local url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$file"

  if [[ -f "$destination" && "$force" -eq 0 ]]; then
    echo "Already exists: $destination"
    return
  fi

  mkdir -p "$(dirname "$destination")"
  echo "Downloading: $url"
  echo "To: $destination"
  curl -L --fail --output "$destination" "$url"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is intended for macOS." >&2
  exit 1
fi

if [[ "$skip_runtime" -eq 0 ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required to install whisper-cpp on macOS." >&2
    echo "Install Homebrew first, or rerun with --skip-runtime if whisper-cli is already available." >&2
    exit 1
  fi

  if command -v whisper-cli >/dev/null 2>&1; then
    echo "whisper-cli already exists: $(command -v whisper-cli)"
  else
    brew install whisper-cpp
  fi
fi

models_dir="$install_root/whisper.cpp/models"
main_model_file="$(model_file "$model")"
language_model_file="$(model_file "$language_model")"
main_model_path="$models_dir/$main_model_file"
language_model_path="$models_dir/$language_model_file"

if [[ "$skip_model" -eq 0 ]]; then
  download_model "$main_model_file" "$main_model_path"
fi

if [[ "$skip_language_model" -eq 0 && "$language_model_file" != "$main_model_file" ]]; then
  download_model "$language_model_file" "$language_model_path"
fi

if [[ "$set_shell_env" -eq 1 ]]; then
  zshrc="$HOME/.zshrc"
  cat >> "$zshrc" <<EOF

# video-report-agent whisper.cpp
export VIDEO_BUNDLE_AGENT_TOOL_ROOT="$install_root"
export VIDEO_BUNDLE_AGENT_WHISPER_MODEL="$main_model_path"
export VIDEO_BUNDLE_AGENT_WHISPER_LANGUAGE_MODEL="$language_model_path"
EOF
  echo "Updated $zshrc. Open a new shell before relying on these environment variables."
fi

echo
echo "whisper.cpp macOS install summary"
echo "Runtime: $(command -v whisper-cli || true)"
echo "Install root: $install_root"
echo "Model: $main_model_path"
echo "Language model: $language_model_path"
echo
echo "Verify with:"
echo "uv run video-bundle-agent doctor"
