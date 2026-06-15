#!/usr/bin/env bash
set -euo pipefail

plugin_name="video-report-agent"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
home_root="$HOME"

usage() {
  cat <<'EOF'
Usage: scripts/install-plugin-macos.sh [options]

Options:
  --plugin-name NAME      Plugin directory/name. Default: video-report-agent
  --project-root PATH     Repository root. Default: parent of scripts/
  --home PATH             User home root. Default: $HOME
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-name)
      plugin_name="$2"
      shift 2
      ;;
    --project-root)
      project_root="$2"
      shift 2
      ;;
    --home)
      home_root="$2"
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

source_dir="$project_root/plugins/$plugin_name"
destination_root="$home_root/plugins"
destination="$destination_root/$plugin_name"
marketplace_dir="$home_root/.agents/plugins"
marketplace_path="$marketplace_dir/marketplace.json"

if [[ ! -f "$source_dir/.codex-plugin/plugin.json" ]]; then
  echo "Plugin source is missing .codex-plugin/plugin.json: $source_dir" >&2
  exit 1
fi

mkdir -p "$destination_root" "$marketplace_dir"

case "$destination" in
  "$destination_root"/*) ;;
  *)
    echo "Refusing to replace destination outside plugin root: $destination" >&2
    exit 1
    ;;
esac

rm -rf "$destination"
cp -R "$source_dir" "$destination"

if command -v python3 >/dev/null 2>&1; then
  python_cmd=(python3)
elif command -v python >/dev/null 2>&1; then
  python_cmd=(python)
elif command -v uv >/dev/null 2>&1; then
  python_cmd=(uv run python)
else
  echo "Python was not found. Install Python 3.12 or uv before installing the plugin." >&2
  exit 1
fi

"${python_cmd[@]}" - "$marketplace_path" "$plugin_name" <<'PY'
import json
import sys
from pathlib import Path

marketplace_path = Path(sys.argv[1])
plugin_name = sys.argv[2]

if marketplace_path.exists():
    data = json.loads(marketplace_path.read_text(encoding="utf-8"))
else:
    data = {
        "name": "personal",
        "interface": {"displayName": "Personal"},
        "plugins": [],
    }

data.setdefault("name", "personal")
data.setdefault("interface", {"displayName": "Personal"})
data.setdefault("plugins", [])

entry = {
    "name": plugin_name,
    "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Productivity",
}

data["plugins"] = [item for item in data["plugins"] if item.get("name") != plugin_name]
data["plugins"].append(entry)

marketplace_path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

echo "Installed plugin source: $destination"
echo "Updated personal marketplace: $marketplace_path"
echo "Next: install or refresh Video Report Agent from the Codex app plugin UI."
