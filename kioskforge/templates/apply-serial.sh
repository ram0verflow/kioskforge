#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OVERLAY_ROOT}/config.json"

python3 - <<'PY' "$CONFIG"
import json, pathlib, subprocess, sys

devices = json.load(open(sys.argv[1])).get("serial_devices") or []
if not devices:
    raise SystemExit(0)

lines = []
for dev in devices:
    lines.append(
        'SUBSYSTEM=="tty", ATTRS{{serial}}=="{usb_serial}", SYMLINK+="{symlink}", '
        'GROUP="{group}", MODE="{mode}"'.format(**dev)
    )

path = pathlib.Path("/etc/udev/rules.d/99-kioskforge-serial.rules")
path.write_text("\n".join(lines) + "\n")
subprocess.run(["udevadm", "control", "--reload-rules"], check=True)
subprocess.run(["udevadm", "trigger"], check=True)
print(f"kioskforge: installed {len(devices)} udev serial rule(s)")
PY
