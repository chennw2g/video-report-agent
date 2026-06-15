#!/usr/bin/env bash
set -euo pipefail

platform="youtube"
url=""
output=""
port="9223"
port_provided=0
domains=""
browser_path=""
user_data_dir=""
use_default_profile=0
keep_browser_open=0
open_only=0
no_prompt=0
node_path=""

usage() {
  cat <<'EOF'
Usage: scripts/refresh-cookies-macos.sh [options]

Options:
  --platform youtube|bilibili|xiaohongshu
  --url URL                  Page to open for login
  --output PATH              Netscape cookie output path
  --port PORT                Chrome DevTools port
  --domains LIST             Comma-separated cookie domains
  --browser-path PATH        Chrome or Edge executable path
  --user-data-dir PATH       Dedicated browser profile directory
  --use-default-profile      Use the browser default profile
  --keep-browser-open        Do not close the launched browser process
  --open-only                Open browser and stop before exporting
  --no-prompt                Wait briefly instead of prompting for Enter
  --node-path PATH           Node executable path
  -h, --help                 Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      platform="$2"
      shift 2
      ;;
    --url)
      url="$2"
      shift 2
      ;;
    --output)
      output="$2"
      shift 2
      ;;
    --port)
      port="$2"
      port_provided=1
      shift 2
      ;;
    --domains)
      domains="$2"
      shift 2
      ;;
    --browser-path)
      browser_path="$2"
      shift 2
      ;;
    --user-data-dir)
      user_data_dir="$2"
      shift 2
      ;;
    --use-default-profile)
      use_default_profile=1
      shift
      ;;
    --keep-browser-open)
      keep_browser_open=1
      shift
      ;;
    --open-only)
      open_only=1
      shift
      ;;
    --no-prompt)
      no_prompt=1
      shift
      ;;
    --node-path)
      node_path="$2"
      shift 2
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

case "$platform" in
  youtube)
    : "${url:=https://www.youtube.com/}"
    : "${output:=$HOME/Library/Application Support/video-bundle-agent/youtube.cookies.txt}"
    : "${domains:=youtube.com,google.com,googleusercontent.com,googlevideo.com,ytimg.com}"
    ;;
  bilibili)
    : "${url:=https://www.bilibili.com/}"
    : "${output:=$HOME/Library/Application Support/video-bundle-agent/bilibili.cookies.txt}"
    : "${domains:=bilibili.com}"
    if [[ "$port_provided" -eq 0 ]]; then
      port="9224"
    fi
    ;;
  xiaohongshu)
    : "${url:=https://www.xiaohongshu.com/explore}"
    : "${output:=$HOME/Library/Application Support/video-bundle-agent/xiaohongshu.cookies.txt}"
    : "${domains:=xiaohongshu.com,xhslink.com}"
    if [[ "$port_provided" -eq 0 ]]; then
      port="9226"
    fi
    ;;
  *)
    echo "Unsupported platform: $platform" >&2
    exit 2
    ;;
esac

if [[ -z "$browser_path" ]]; then
  for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"; do
    if [[ -x "$candidate" ]]; then
      browser_path="$candidate"
      break
    fi
  done
fi
if [[ -z "$browser_path" ]]; then
  echo "Chrome or Edge was not found. Pass --browser-path." >&2
  exit 1
fi

if [[ -z "$node_path" ]]; then
  if command -v node >/dev/null 2>&1; then
    node_path="$(command -v node)"
  else
    echo "Node.js was not found. Install Node or pass --node-path." >&2
    exit 1
  fi
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exporter="$project_root/scripts/export-youtube-cookies-cdp.mjs"
if [[ ! -f "$exporter" ]]; then
  echo "Missing exporter script: $exporter" >&2
  exit 1
fi

browser_args=(
  "--remote-debugging-address=127.0.0.1"
  "--remote-debugging-port=$port"
  "--new-window"
  "$url"
)

if [[ "$use_default_profile" -eq 0 ]]; then
  : "${user_data_dir:=$HOME/Library/Application Support/video-bundle-agent/chrome-$platform-profile}"
  mkdir -p "$user_data_dir"
  browser_args=("--user-data-dir=$user_data_dir" "${browser_args[@]}")
fi

echo "Opening browser for $platform cookie refresh."
echo "Browser: $browser_path"
echo "Cookie output: $output"
if [[ "$use_default_profile" -eq 0 ]]; then
  echo "Profile: $user_data_dir"
else
  echo "Profile: default browser profile"
fi

"$browser_path" "${browser_args[@]}" &
browser_pid=$!

if [[ "$open_only" -eq 1 ]]; then
  echo "Browser is open. Sign in, then rerun without --open-only."
  exit 0
fi

if [[ "$no_prompt" -eq 1 ]]; then
  sleep 5
else
  echo
  echo "Sign in if needed. After the page loads, press Enter here."
  read -r _
fi

"$node_path" "$exporter" --port "$port" --output "$output" --domains "$domains"

echo "Cookies exported. Pass this file with --cookies \"$output\"."

if [[ "$keep_browser_open" -eq 0 ]]; then
  kill "$browser_pid" >/dev/null 2>&1 || true
fi
