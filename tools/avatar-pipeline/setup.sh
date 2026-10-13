#!/usr/bin/env bash
# One-time setup: downloads MPFB2 + the MakeHuman CC0 system asset pack and installs MPFB into an
# isolated Blender profile under .work/ (your personal Blender configuration is not modified).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${AVATAR_WORK:-$HERE/.work}"
BLENDER="${BLENDER_EXE:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
MPFB_TAG="v2.0.18"
mkdir -p "$WORK" && cd "$WORK"
curl -sL -o mpfb2.zip "https://github.com/makehumancommunity/mpfb2/archive/refs/tags/$MPFB_TAG.zip"
curl -sL -C - --retry 5 -o mh_assets.zip "http://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip"
unzip -q -o mpfb2.zip
export BLENDER_USER_RESOURCES="$WORK/blender_profile"
"$BLENDER" --command extension build --source-dir "mpfb2-${MPFB_TAG#v}/src/mpfb" --output-dir .
"$BLENDER" --command extension install-file -r user_default --enable "mpfb-${MPFB_TAG#v}.zip"
DATA="$BLENDER_USER_RESOURCES/extensions/.user/user_default/mpfb/data"
mkdir -p "$DATA" && unzip -q -o mh_assets.zip -d "$DATA"
# Extra CC0 packs (dresses, shirts/sweaters, pants, skirts, shoes, suits, beards) used by build_avatar.py.
for pack in dress01 shirts01 pants01 skirts01 shoes01 suits01 bodyparts05; do
  curl -sL -C - --retry 5 -o "$pack.zip" "https://files.makehumancommunity.org/asset_packs/$pack/${pack}_cc0.zip"
  mkdir -p "packs/$pack" && unzip -q -o "$pack.zip" -d "packs/$pack"
  cp -r "packs/$pack/clothes/." "$DATA/clothes/"
done
echo "SETUP DONE ($WORK)"
