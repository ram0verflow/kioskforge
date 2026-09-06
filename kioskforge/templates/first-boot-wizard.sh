#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OVERLAY_ROOT}/config.json"
MARKER="/var/lib/kioskforge/wizard-done"

python3 - <<'PY' "$CONFIG" "$MARKER"
import json, os, sys

cfg = json.load(open(sys.argv[1]))
marker = sys.argv[2]
if os.path.exists(marker) or not cfg.get("first_boot_wizard"):
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    open(marker, "a").close()
    raise SystemExit(0)

print("\n=== Kioskforge first-boot wizard ===\n")
hostname = input(f"Hostname [{cfg.get('hostname', 'kiosk')}]: ").strip() or cfg.get("hostname", "kiosk")
url = input(f"Primary URL [{cfg.get('urls', [''])[0]}]: ").strip()
if url:
    cfg.setdefault("urls", [])
    if cfg["urls"]:
        cfg["urls"][0] = url
    else:
        cfg["urls"] = [url]
    flags = "--kiosk --noerrdialogs --disable-infobars --no-first-run"
    cfg["chromium_command"] = "chromium " + flags + " " + " ".join(f'"{u}"' for u in cfg["urls"])
cfg["hostname"] = hostname
with open(sys.argv[1], "w") as f:
    json.dump(cfg, f, indent=2)
os.makedirs(os.path.dirname(marker), exist_ok=True)
open(marker, "w").close()
print("\nWizard saved.\n")
PY
