#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OVERLAY_ROOT}/config.json"

python3 - <<'PY' "$CONFIG" "$OVERLAY_ROOT"
import json, pathlib, shutil, subprocess, sys

cfg = json.load(open(sys.argv[1]))
overlay = pathlib.Path(sys.argv[2])
docker_cfg = cfg.get("docker") or {}
if not docker_cfg.get("enabled"):
    raise SystemExit(0)

work = pathlib.Path(docker_cfg["working_dir"])
work.mkdir(parents=True, exist_ok=True)
compose_name = docker_cfg.get("compose_filename", "docker-compose.yml")
src = overlay / "docker" / compose_name
if src.is_file():
    shutil.copy2(src, work / compose_name)

install_sh = subprocess.run(
    ["curl", "-fsSL", "https://get.docker.com"],
    capture_output=True,
    text=True,
    check=True,
).stdout
subprocess.run(["sh"], input=install_sh, text=True, check=True)
subprocess.run(["apt-get", "install", "-y", "-qq", "docker-compose-plugin"], check=False)
subprocess.run(["systemctl", "enable", "--now", "docker"], check=True)

unit = f"""[Unit]
Description=Kioskforge Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={work}
ExecStart=/usr/bin/docker compose -f {compose_name} up -d
ExecStop=/usr/bin/docker compose -f {compose_name} down

[Install]
WantedBy=multi-user.target
"""
pathlib.Path("/etc/systemd/system/kioskforge-docker.service").write_text(unit)
subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["systemctl", "enable", "kioskforge-docker.service"], check=True)
subprocess.run(["systemctl", "start", "kioskforge-docker.service"], check=True)
print("kioskforge: docker compose enabled")
PY
