#!/usr/bin/env python3
"""Sign and fully verify the original SystemOS cryptex image without expanding the UDIF.

Runner-side companion of scripts/build-owner-os-policy.py: the SystemOS policy anchors
the raw compressed UDIF bytes, so no hdiutil expansion is needed for verification; the
volume UUID is read once from a read-only attachment of the same image.
"""
import ctypes, hashlib, importlib.util, json, plistlib, subprocess, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / ".cache/firmware/target-volumes/044-76034-038.dmg"
out = ROOT / "build/verified-root-systemos"
EXPECTED_SIZE = 3303014400
EXPECTED_DIGEST = "b4908cde41d23e6bc05e6af51a2c9eeb00cf0f863a6a18b1600c96a3fd70414f"

if not source.is_file() or source.stat().st_size != EXPECTED_SIZE:
    raise SystemExit("Require the exact original SystemOS input")
digest = hashlib.sha256()
with source.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != EXPECTED_DIGEST:
    raise SystemExit("The compressed image must be the exact supplied SystemOS member")

attached = plistlib.loads(subprocess.check_output(
    ["hdiutil", "attach", "-readonly", "-nobrowse", "-plist", str(source)]))
entities = attached["system-entities"]
mounted = [e for e in entities if e.get("mount-point")]
if len(mounted) != 1:
    raise SystemExit("Require exactly one mounted SystemOS volume")
info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", mounted[0]["dev-entry"]]))
volume_uuid = uuid.UUID(info["VolumeUUID"])
subprocess.run(["hdiutil", "detach", mounted[0]["dev-entry"]], check=True, capture_output=True)
print("SystemOS volume UUID:", volume_uuid)

spec = importlib.util.spec_from_file_location("verified_manifest", ROOT / "kits/VerifiedRoot/tools/manifest.py")
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)
keys = ROOT / "build/verified-root-host/keys"
with source.open("rb", buffering=1024 * 1024) as stream:
    record = manifest.make(stream, EXPECTED_SIZE, keys / "owner.pem", keys / "owner-public.pem",
                           volume_uuid, 1, out)


class View(ctypes.Structure):
    _fields_ = [("hashes", ctypes.c_void_p), ("image_bytes", ctypes.c_uint64), ("block_count", ctypes.c_uint64),
                ("generation", ctypes.c_uint64), ("volume_uuid", ctypes.c_uint8 * 16), ("image_sha256", ctypes.c_uint8 * 32)]


native = ctypes.CDLL(str(ROOT / "build/verified-root-host/verified-root.dylib"))
native.vr_host_open.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(View)]
native.vr_host_block.argtypes = [ctypes.POINTER(View), ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
encoded = ctypes.create_string_buffer((out / "manifest.bin").read_bytes())
anchor = ctypes.create_string_buffer((out / "trusted-key.bin").read_bytes())
view = View()
if native.vr_host_open(encoded, len(encoded) - 1, anchor, 1, ctypes.byref(view)) or bytes(view.volume_uuid) != volume_uuid.bytes:
    raise SystemExit("Real C signature/volume authentication failed")
complete = hashlib.sha256()
with source.open("rb", buffering=1024 * 1024) as stream:
    for index in range(view.block_count):
        block = stream.read(min(4096, view.image_bytes - index * 4096))
        if native.vr_host_block(ctypes.byref(view), index, block, len(block)) != 0:
            raise SystemExit("Actual C block verification failed at " + str(index))
        complete.update(block)
    if stream.read(1):
        raise SystemExit("Image exceeded its authenticated exact bounds")
if complete.hexdigest() != record["image_sha256"]:
    raise SystemExit("Actual complete original SystemOS digest differs")
report = dict(image_bytes=view.image_bytes, blocks_verified=view.block_count, image_sha256=complete.hexdigest(),
              volume_uuid=str(volume_uuid).upper(), generation=view.generation,
              source_compressed_sha256=digest.hexdigest(), source_format="UDIF",
              host_bus_protocol="Disk Image", host_media_writable=False,
              trusted_key_sha256=record["trusted_key_sha256"], real_c_signature_and_block_verification=True,
              original_image_modified=False, host_only=True, boot_root_authenticated=False,
              qemu_tested=False, hardware_tested=False)
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
print("PASS: original SystemOS signature and every", view.block_count, "block verified by real C/RSA; no expanded image")
