#!/bin/bash
# Build the sheng Metal add-on on a macOS runner from the offline ci-inputs branch.
set -euxo pipefail

exec > >(tee ci-metal-addon.log) 2>&1
trap 'rc=$?; echo "::error::ci-metal-addon failed (rc=$rc) at line $LINENO"; exit $rc' ERR

echo "== host tools =="
brew install meson ninja glslang bison rustup llvm shaderc spirv-tools pkg-config vulkan-headers vulkan-loader
export PATH="/opt/homebrew/opt/bison/bin:/opt/homebrew/opt/llvm/bin:$PATH"
rustup toolchain install 1.98.0 --profile minimal
rustup default 1.98.0
rustup target add aarch64-apple-ios --toolchain 1.98.0
rustup +1.98.0 target list --installed
export PATH="/opt/homebrew/opt/rustup/bin:$PATH"
command -v cargo
cargo --version
bison --version | head -1
llvm-as --version | head -1
glslc --version | head -1
spirv-val --version | head -1
glslangValidator --version | head -1

echo "== mesa source =="
test -d .cache/mesa-work
git -C .cache/mesa-work rev-parse HEAD
git -C .cache/mesa-work status --short | head -30

echo "== mesa venv =="
python3 -m venv .cache/mesa-venv
.cache/mesa-venv/bin/pip install -q --upgrade pip
.cache/mesa-venv/bin/pip install -q meson ninja packaging mako pyyaml
.cache/mesa-venv/bin/meson --version

echo "== turnip host =="
python3 scripts/build-turnip-darwin.py --target host

echo "== turnip ios =="
python3 scripts/build-turnip-darwin.py --target ios

echo "== host smoke =="
python3 scripts/ci-host-smoke.py

echo "== metal2vulkan source =="
test -d .cache/gpu-reference/metal2vulkan
git -C .cache/gpu-reference/metal2vulkan rev-parse HEAD

echo "== plugin =="
python3 scripts/build-adreno-metal-plugin.py
ls -la build/adreno-metal-plugin
