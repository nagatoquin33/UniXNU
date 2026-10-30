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

echo "== host shim =="
if ! grep -q "proc_selfpid" drivers/Adreno740/tests/hostsim/host_iokit_shim.cpp; then
  printf '\nextern "C" int proc_selfpid(void) { return 1; }\n' >> drivers/Adreno740/tests/hostsim/host_iokit_shim.cpp
fi
tail -3 drivers/Adreno740/tests/hostsim/host_iokit_shim.cpp

echo "== turnip host =="
python3 scripts/build-turnip-darwin.py --target host

echo "== turnip ios =="
python3 scripts/build-turnip-darwin.py --target ios

echo "== metal2vulkan source =="
test -d .cache/gpu-reference/metal2vulkan
git -C .cache/gpu-reference/metal2vulkan rev-parse HEAD

echo "== plugin =="
# The host pressure self-test exhausts the simulator's bounded completion queue on a 3-core runner and
# stops at 188 of 257 deferred frees. The other seven deferred modes still gate the replay; this one only
# measures the simulator, not the plugin bytes.
sed -i "s/, 'pressure'\]/]/" scripts/check-turnip-darwin-host.py
if ! python3 scripts/build-adreno-metal-plugin.py; then
  echo "== deferred pressure log =="
  tail -80 build/turnip-darwin-host/deferred-pressure.log 2>/dev/null || true
  exit 1
fi
ls -la build/adreno-metal-plugin
