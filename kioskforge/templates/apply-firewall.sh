#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OVERLAY_ROOT}/config.json"

python3 - <<'PY' "$CONFIG"
import json, subprocess, sys

cfg = json.load(open(sys.argv[1]))
fw = cfg.get("firewall") or {}
if not fw.get("enabled"):
    print("kioskforge: firewall disabled")
    raise SystemExit(0)

subprocess.run(["apt-get", "update", "-qq"], check=False)
subprocess.run(["DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "-qq", "ufw"], check=True)

default_out = "allow" if fw.get("allow_outbound", True) else "deny"
subprocess.run(["ufw", "default", "deny", "incoming"], check=True)
subprocess.run(["ufw", "default", default_out, "outgoing"], check=True)

if fw.get("allow_ssh", True):
    port = cfg.get("ssh_port")
    if port:
        subprocess.run(["ufw", "allow", str(port), "/tcp"], check=True)
    else:
        subprocess.run(["ufw", "allow", "OpenSSH"], check=True)

for port in fw.get("allow_ports") or []:
    subprocess.run(["ufw", "allow", str(port)], check=True)

for iface in fw.get("allow_interfaces") or []:
    subprocess.run(["ufw", "allow", "in", "on", iface], check=True)

subprocess.run(["ufw", "--force", "enable"], check=True)
print("kioskforge: ufw enabled")
PY
