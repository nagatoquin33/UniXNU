#!/bin/bash
# Build the sheng Metal add-on on a macOS runner from the offline ci-inputs branch.
set -euxo pipefail

exec > >(tee ci-metal-addon.log) 2>&1
trap 'rc=$?; echo "::error::ci-metal-addon failed (rc=$rc) at line $LINENO"; exit $rc' ERR

echo "== host tools =="
brew install meson ninja glslang bison rust llvm

echo "== mesa source =="
test -d .cache/mesa-work
git -C .cache/mesa-work rev-parse HEAD
git -C .cache/mesa-work status --short | head -30

echo "== mesa venv =="
python3 -m venv .cache/mesa-venv
.cache/mesa-venv/bin/pip install -q --upgrade pip
.cache/mesa-venv/bin/pip install -q meson ninja packaging mako pyyaml
.cache/mesa-venv/bin/meson --version

echo "== turnip ios =="
python3 scripts/build-turnip-darwin.py --target ios

echo "== metal2vulkan source =="
test -d .cache/gpu-reference/metal2vulkan
git -C .cache/gpu-reference/metal2vulkan rev-parse HEAD

echo "== plugin =="
python3 scripts/build-adreno-metal-plugin.py
ls -la build/adreno-metal-plugin
