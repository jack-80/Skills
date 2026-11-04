#!/bin/zsh
# Render a Remotion composition to MP4 with the environment fixes baked in.
# Usage: render.sh <project_dir> <composition_id> <output_file>
set -e
PROJECT_DIR="${1:?project dir required}"
COMP_ID="${2:?composition id required}"
OUT="${3:-output/video.mp4}"
cd "$PROJECT_DIR"
mkdir -p .tmp "$(dirname "$OUT")"
env -u NODE_OPTIONS \
  TMPDIR="$PROJECT_DIR/.tmp" \
  PATH="/Users/jack/.workbuddy/binaries/node/versions/22.22.2-6/bin:$PATH" \
  npx remotion render src/index.ts "$COMP_ID" "$OUT" 2>&1 | tail -3
ls -la "$(dirname "$OUT")"
