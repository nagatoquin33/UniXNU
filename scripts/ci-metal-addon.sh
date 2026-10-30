#!/bin/bash
# Build the sheng Metal add-on on a macOS runner.
set -euxo pipefail

echo "== host tools =="
brew install meson ninja glslang bison rust llvm

echo "== mesa source =="
mkdir -p .cache
rm -rf .cache/mesa-work
git init -q .cache/mesa-work
git -C .cache/mesa-work remote add origin https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa
git -C .cache/mesa-work fetch --depth 1 origin 85fda3b36405bcaea8bffc64aa4f2651dc90770d
git -C .cache/mesa-work checkout -q FETCH_HEAD
git -C .cache/mesa-work sparse-checkout init --cone
dirs=$(python3 -c "import json;print(' '.join(json.load(open('scripts/data/adreno-compiler-inputs.json'))['mesa']['sparse_directories']))")
git -C .cache/mesa-work sparse-checkout set $dirs
git -C .cache/mesa-work rev-parse HEAD

echo "== mesa patches =="
for p in $(python3 -c "import json;print(' '.join(json.load(open('scripts/data/adreno-compiler-inputs.json'))['patches']))"); do
  echo "applying $p"
  git -C .cache/mesa-work apply "$p"
done
git -C .cache/mesa-work status --short | head -30

echo "== mesa venv =="
python3 -m venv .cache/mesa-venv
.cache/mesa-venv/bin/pip install -q --upgrade pip
.cache/mesa-venv/bin/pip install -q meson ninja
.cache/mesa-venv/bin/meson --version

echo "== turnip ios =="
python3 scripts/build-turnip-darwin.py --target ios

echo "== metal2vulkan source =="
mkdir -p .cache/gpu-reference
rm -rf .cache/gpu-reference/metal2vulkan
git init -q .cache/gpu-reference/metal2vulkan
git -C .cache/gpu-reference/metal2vulkan remote add origin https://github.com/steelbrain/metal2vulkan
git -C .cache/gpu-reference/metal2vulkan fetch --depth 1 origin 720ef1ce9ae2a2068999a8675717418b9416283e
git -C .cache/gpu-reference/metal2vulkan checkout -q FETCH_HEAD
git -C .cache/gpu-reference/metal2vulkan rev-parse HEAD

echo "== plugin =="
python3 scripts/build-adreno-metal-plugin.py
ls -la build/adreno-metal-plugin
