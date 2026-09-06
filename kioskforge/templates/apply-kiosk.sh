#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OVERLAY_ROOT}/config.json"
USER="${KIOSKFORGE_USER:-pi}"
HOME_DIR="/home/${USER}"

python3 - <<'PY' "$CONFIG" "$HOME_DIR" "$USER"
import json, os, pathlib, stat, subprocess, sys

cfg = json.load(open(sys.argv[1]))
home = pathlib.Path(sys.argv[2])
user = sys.argv[3]
display = cfg.get("display", "wayland")
rotate = int(cfg.get("tab_rotate_seconds") or 0)
hide = bool(cfg.get("hide_cursor", True))
chromium_cmd = cfg.get("chromium_command", "chromium --kiosk about:blank")

bin_dir = home / "bin"
bin_dir.mkdir(parents=True, exist_ok=True)
config_dir = home / ".config"
config_dir.mkdir(parents=True, exist_ok=True)

run_sh = bin_dir / "kioskforge-run-chromium.sh"
run_sh.write_text("#!/usr/bin/env bash\nsleep 4\n" + chromium_cmd + " &\n")
run_sh.chmod(run_sh.stat().st_mode | stat.S_IXUSR)

if rotate > 0:
    rot = bin_dir / "kioskforge-rotate-tabs.sh"
    rot.write_text(
        "#!/usr/bin/env bash\nsleep 8\nwhile true; do\n"
        f"  wtype -M ctrl -P Tab -p Tab 2>/dev/null || true\n  sleep {rotate}\n"
        "done\n"
    )
    rot.chmod(rot.stat().st_mode | stat.S_IXUSR)

if hide:
    hid = bin_dir / "kioskforge-hide-cursor.sh"
    hid.write_text(
        "#!/usr/bin/env bash\nsleep 8\n"
        "command -v ydotool >/dev/null && ydotool mousemove 10000 10000 || true\n"
    )
    hid.chmod(hid.stat().st_mode | stat.S_IXUSR)

if display == "wayland":
    labwc = config_dir / "labwc"
    labwc.mkdir(parents=True, exist_ok=True)
    lines = [
        "screen -s 0 dpms off",
        "screen -s 0 -d 0",
        f"{run_sh} &",
    ]
    if rotate > 0:
        lines.append(f"{bin_dir / 'kioskforge-rotate-tabs.sh'} &")
    if hide:
        lines.append(f"{bin_dir / 'kioskforge-hide-cursor.sh'} &")
    (labwc / "autostart").write_text("\n".join(lines) + "\n")
else:
    lx = config_dir / "lxsession" / "LXDE-pi"
    lx.mkdir(parents=True, exist_ok=True)
    (lx / "autostart").write_text(
        "@xset s off\n@xset -dpms\n@xset s noblank\n@" + str(run_sh) + "\n"
    )

subprocess.run(["chown", "-R", f"{user}:{user}", str(home / "bin"), str(config_dir)], check=False)

pkgs = ["wtype"]
if hide:
    pkgs.append("ydotool")
subprocess.run(["apt-get", "update", "-qq"], check=False)
subprocess.run(["DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "-qq", *pkgs], check=False)
print(f"kioskforge: kiosk autostart configured ({display})")
PY
