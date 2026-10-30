#!/usr/bin/env python3
"""Build only the host transport and plugin smoke that the replay generator runs.

check-turnip-darwin-host.py compiles these two binaries and then runs the full host verification
suite: the Vulkan smoke, eight deferred-BO modes, the pipeline cache control, the QuartzCore driver
cache control and the priming cache control. Those checks need the original UI caches and driver
feedback fixtures; the replay generator needs only the binaries. This builds them and stops.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
kit = ROOT / 'drivers/Adreno740'
sim = kit / 'tests/hostsim'
smmu = ROOT / 'kits/ArmSmmu4K'
out = ROOT / 'build/turnip-darwin-host'
out.mkdir(parents=True, exist_ok=True)
library = ROOT / 'build/mesa-tu/src/freedreno/vulkan/libvulkan_freedreno.dylib'
if not library.exists():
    sys.exit('Build the host Turnip first: python3 scripts/build-turnip-darwin.py --target host')

includes = out / 'host-include'
for name in ['IOKit/IOTypes.h', 'IOKit/IOReturn.h', 'IOKit/IOBufferMemoryDescriptor.h', 'IOKit/IOLib.h', 'kern/task.h']:
    path = includes / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#include "XnuMemoryFixture.h"\n')

objects = []
for stem in ['ArmSmmu4KContext', 'ArmSmmu4KProgram', 'ArmSmmu4KLive', 'ArmSmmu4KStreams', 'ArmSmmu4KMmio']:
    obj = out / (stem + '.o')
    subprocess.run(['xcrun', 'clang', '-std=c11', '-O1', '-fPIC', '-c', smmu / (stem + '.c'), '-o', obj], check=True)
    objects.append(obj)
obj = out / 'AdrenoPM4.o'
subprocess.run(['xcrun', 'clang', '-std=c11', '-O1', '-fPIC', '-c', ROOT / 'kits/AdrenoPM4/AdrenoPM4.c', '-o', obj], check=True)
objects.append(obj)

service = out / 'host_gpu_service.o'
subprocess.run(['xcrun', 'clang++', '-std=c++23', '-O1', '-fPIC', '-I', includes, '-I', sim.parent, '-I', kit, '-I', smmu,
                '-I', ROOT / 'kits/AdrenoPM4', '-c', sim / 'host_gpu_service.cpp', '-o', service], check=True)
core = []
for name in ['NativeAdrenoMemory', 'NativeAdrenoSmmuMemory', 'NativeAdrenoVm', 'NativeAdrenoRing', 'NativeAdrenoSubmit',
             'NativeAdrenoUserClient', 'NativeAdrenoTimer', 'NativeAdrenoSmmuContext', 'NativeAdrenoGpuContext']:
    obj = out / (name + '.o')
    subprocess.run(['xcrun', 'clang++', '-std=c++23', '-O1', '-fPIC', '-I', includes, '-I', sim.parent, '-I', kit, '-I', smmu,
                    '-I', ROOT / 'kits/AdrenoPM4', '-c', kit / (name + '.cpp'), '-o', obj], check=True)
    core.append(obj)

shim_source = sim / 'host_iokit_shim.cpp'
text = shim_source.read_text()
if 'proc_selfpid' not in text:
    shim_source.write_text(text + '\nextern "C" int proc_selfpid(void) { return 1; }\n')

shim_obj = out / 'host_iokit_shim.o'
subprocess.run(['xcrun', 'clang++', '-std=c++17', '-O1', '-fPIC', '-c', shim_source, '-o', shim_obj], check=True)
shim = out / 'libhostiokit.dylib'
subprocess.run(['xcrun', 'clang++', '-dynamiclib', '-o', shim, service, shim_obj, *core, *objects,
                '-framework', 'IOKit', '-framework', 'CoreFoundation'], check=True)

subprocess.run([sys.executable, ROOT / 'scripts/gen-turnip-smoke-shaders.py'], check=True)
plugin_smoke = out / 'plugin_smoke'
subprocess.run(['xcrun', 'clang++', '-std=c++17', '-O1', '-I', ROOT / 'drivers/AdrenoMetal',
                '-I', ROOT / '.cache/mesa-work/include', '-I', ROOT / 'build/turnip-smoke',
                sim / 'plugin_smoke.cpp', '-o', plugin_smoke], check=True)
print('PASS: host transport and plugin smoke built at', out)
