#!/usr/bin/env bash
# Builds the avatar assets. Usage: tools/avatar-pipeline/build_all.sh frontend/public/models/avatar
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
export AVATAR_WORK="${AVATAR_WORK:-$HERE/.work}"
export BLENDER_USER_RESOURCES="$AVATAR_WORK/blender_profile"
BLENDER="${BLENDER_EXE:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
rm -rf "$AVATAR_WORK/out"
for g in female male neutral; do
  "$BLENDER" -b -P "$HERE/build_avatar.py" -- "$AVATAR_WORK/out" "$g" > "$AVATAR_WORK/build_$g.log" 2>&1
  grep -q "BUILD DONE $g" "$AVATAR_WORK/build_$g.log" || { echo "build failed for $g (see $AVATAR_WORK/build_$g.log)"; exit 1; }
done
python "$HERE/remove_logo.py"
python "$HERE/postprocess.py" "$DEST"
# Wrinkle detail maps for the skin shader (from the middle-aged / old MakeHuman skins).
python "$HERE/age_detail.py" "$AVATAR_WORK/blender_profile/extensions/.user/user_default/mpfb/data" "$DEST/tex"
echo "PIPELINE DONE -> $DEST (now re-render thumbnails: cd frontend && node scripts/render-avatar-thumbnails.mjs)"
