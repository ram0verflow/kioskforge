#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OVERLAY_ROOT}/config.json"

python3 - <<'PY' "$CONFIG"
import json, os, subprocess, sys

cfg = json.load(open(sys.argv[1]))
if not (cfg.get("tailscale") or {}).get("enabled"):
    raise SystemExit(0)

key = os.environ.get("KIOSKFORGE_TAILSCALE_AUTHKEY", "").strip()
if not key:
    print("kioskforge: tailscale enabled but KIOSKFORGE_TAILSCALE_AUTHKEY not set", file=sys.stderr)
    raise SystemExit(1)

install_sh = subprocess.run(
    ["curl", "-fsSL", "https://tailscale.com/install.sh"],
    capture_output=True,
    text=True,
    check=True,
).stdout
subprocess.run(["sh"], input=install_sh, text=True, check=True)
subprocess.run(["tailscale", "up", "--authkey", key], check=True)
print("kioskforge: tailscale connected")
PY
