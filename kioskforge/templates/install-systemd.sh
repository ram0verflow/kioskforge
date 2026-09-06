#!/usr/bin/env bash
set -euo pipefail

OVERLAY_ROOT="${1:-/boot/firmware/kioskforge}"
USER="${2:-pi}"
MARKER="/var/lib/kioskforge/firstboot-done"

if [[ -f "$MARKER" ]]; then
  echo "kioskforge: already provisioned"
  exit 0
fi

export OVERLAY_ROOT
export KIOSKFORGE_USER="$USER"
mkdir -p /var/lib/kioskforge

python3 - <<'PY' "${OVERLAY_ROOT}/config.json"
import json, subprocess, sys
pkgs = json.load(open(sys.argv[1])).get("packages") or []
if pkgs:
    subprocess.run(["apt-get", "update", "-qq"], check=False)
    subprocess.run(["DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "-qq", *pkgs], check=True)
PY

python3 - <<'PY' "${OVERLAY_ROOT}/config.json"
import json, sys
env = json.load(open(sys.argv[1])).get("env") or {}
if env:
    open("/etc/kioskforge.env", "w").write("\n".join(f'{k}="{v}"' for k, v in env.items()) + "\n")
PY

if python3 -c "import json; print(json.load(open('${OVERLAY_ROOT}/config.json')).get('hostname_from_mac'))" | grep -q True; then
  IFACE=$(ip -o link show | awk -F': ' '$2 !~ /lo/ {print $2; exit}')
  MAC=$(cat "/sys/class/net/${IFACE}/address" | tr -d ':' | tail -c 7)
  NEW_HOST="kiosk-${MAC}"
  echo "$NEW_HOST" > /etc/hostname
  sed -i "s/127.0.1.1.*/127.0.1.1\t${NEW_HOST}/" /etc/hosts
  hostname "$NEW_HOST"
else
  H="$(python3 -c "import json; print(json.load(open('${OVERLAY_ROOT}/config.json')).get('hostname','kiosk'))")"
  echo "$H" > /etc/hostname
  sed -i "s/127.0.1.1.*/127.0.1.1\t${H}/" /etc/hosts
  hostname "$H"
fi

bash "${OVERLAY_ROOT}/scripts/first-boot-wizard.sh"
bash "${OVERLAY_ROOT}/scripts/apply-serial.sh"
bash "${OVERLAY_ROOT}/scripts/apply-firewall.sh"
bash "${OVERLAY_ROOT}/scripts/apply-docker.sh"
bash "${OVERLAY_ROOT}/scripts/apply-tailscale.sh"
bash "${OVERLAY_ROOT}/scripts/apply-kiosk.sh"

python3 - <<'PY' "${OVERLAY_ROOT}/config.json"
import json, subprocess, sys
for cmd in json.load(open(sys.argv[1])).get("post_install") or []:
    subprocess.run(["bash", "-lc", cmd], check=True)
PY

python3 - <<'PY' "${OVERLAY_ROOT}/config.json"
import json, pathlib, sys
cfg = json.load(open(sys.argv[1]))
path = pathlib.Path("/etc/ssh/sshd_config")
if not path.exists():
    raise SystemExit(0)
text = path.read_text().splitlines()
out = []
port = cfg.get("ssh_port")
for line in text:
    if line.strip().startswith("Port ") and port:
        out.append(f"Port {port}")
    elif line.strip().startswith("#Port ") and port:
        out.append(f"Port {port}")
    elif line.strip().startswith("PasswordAuthentication") and cfg.get("ssh_password_auth") is False:
        out.append("PasswordAuthentication no")
    elif line.strip().startswith("#PasswordAuthentication") and cfg.get("ssh_password_auth") is False:
        out.append("PasswordAuthentication no")
    else:
        out.append(line)
path.write_text("\n".join(out) + "\n")
PY

if python3 -c "import json; print(json.load(open('${OVERLAY_ROOT}/config.json')).get('read_only_root'))" | grep -q True; then
  raspi-config nonint do_overlayfs 0 || true
  raspi-config nonint do_boot_ro 0 || true
fi

systemctl disable kioskforge-firstboot.service 2>/dev/null || true
touch "$MARKER"
echo "kioskforge: provisioning complete"
