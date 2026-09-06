from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

from kioskforge.config import KioskConfig

OVERLAY_DIR = "kioskforge"
SYSTEMD_UNIT = "kioskforge-firstboot.service"
FIRSTRUN_HOOK = "kioskforge-firstrun.sh"


def _template_dir() -> Path:
    return Path(__file__).parent / "templates"


def _read_template(name: str) -> str:
    return (_template_dir() / name).read_text()


def _render(template_name: str, **kwargs: str) -> str:
    content = _read_template(template_name)
    for key, value in kwargs.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def chromium_command(cfg: KioskConfig) -> str:
    urls = " ".join(f'"{u}"' for u in cfg.urls)
    flags = " ".join(cfg.chromium_flags)
    return f"chromium {flags} {urls}"


def _meta_dict(cfg: KioskConfig) -> dict:
    meta: dict = {
        "version": 1,
        "hostname": cfg.hostname,
        "hostname_from_mac": cfg.hostname_from_mac,
        "username": cfg.username,
        "display": cfg.display,
        "urls": cfg.urls,
        "tab_rotate_seconds": cfg.tab_rotate_seconds,
        "first_boot_wizard": cfg.first_boot_wizard,
        "read_only_root": cfg.read_only_root,
        "ssh_password_auth": cfg.ssh_password_auth,
        "ssh_port": cfg.ssh_port,
        "packages": cfg.packages,
        "env": cfg.env,
        "post_install": cfg.post_install,
        "chromium_command": chromium_command(cfg),
        "disable_screen_blank": cfg.disable_screen_blank,
        "hide_cursor": cfg.hide_cursor,
        "docker": {
            "enabled": cfg.docker.enabled,
            "working_dir": cfg.docker.working_dir,
            "compose_filename": cfg.docker.compose_filename,
        },
        "tailscale": {"enabled": cfg.tailscale.enabled},
        "serial_devices": [
            {
                "symlink": d.symlink,
                "usb_serial": d.usb_serial,
                "group": d.group,
                "mode": d.mode,
            }
            for d in cfg.serial_devices
        ],
        "display_hdmi": cfg.display_hdmi,
        "firewall": None,
    }
    if cfg.firewall:
        meta["firewall"] = {
            "enabled": cfg.firewall.enabled,
            "allow_ssh": cfg.firewall.allow_ssh,
            "allow_outbound": cfg.firewall.allow_outbound,
            "allow_ports": cfg.firewall.allow_ports,
            "allow_interfaces": cfg.firewall.allow_interfaces,
        }
    return meta


def generate_overlay(
    cfg: KioskConfig,
    output_dir: Path,
    compose_source: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay = output_dir / OVERLAY_DIR
    if overlay.exists():
        shutil.rmtree(overlay)
    overlay.mkdir()

    (overlay / "config.json").write_text(json.dumps(_meta_dict(cfg), indent=2) + "\n")

    scripts = overlay / "scripts"
    scripts.mkdir()
    for name in (
        "apply-kiosk.sh",
        "apply-firewall.sh",
        "apply-docker.sh",
        "apply-serial.sh",
        "apply-tailscale.sh",
        "first-boot-wizard.sh",
        "install-systemd.sh",
    ):
        dest = scripts / name
        dest.write_text(_read_template(name))
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    (overlay / "systemd").mkdir()
    unit = _render(
        "kioskforge-firstboot.service",
        overlay_path=f"/boot/firmware/{OVERLAY_DIR}",
        username=cfg.username,
    )
    (overlay / "systemd" / SYSTEMD_UNIT).write_text(unit)

    if cfg.docker.enabled and compose_source and compose_source.is_file():
        docker_dir = overlay / "docker"
        docker_dir.mkdir()
        shutil.copy2(compose_source, docker_dir / cfg.docker.compose_filename)

    firstrun = _render(
        FIRSTRUN_HOOK,
        overlay_dir=OVERLAY_DIR,
        systemd_unit=SYSTEMD_UNIT,
    )
    (output_dir / FIRSTRUN_HOOK).write_text(firstrun)
    (output_dir / FIRSTRUN_HOOK).chmod(
        (output_dir / FIRSTRUN_HOOK).stat().st_mode | stat.S_IXUSR
    )

    (output_dir / "README.inject.md").write_text(
        _render("OVERLAY_README.md", hostname=cfg.hostname, overlay_dir=OVERLAY_DIR)
    )
    return overlay


def inject_boot_partition(
    cfg: KioskConfig,
    boot_mount: Path,
    compose_source: Path | None = None,
) -> Path:
    boot_mount = boot_mount.resolve()
    if not boot_mount.is_dir():
        raise FileNotFoundError(f"Boot mount not found: {boot_mount}")

    staging = boot_mount / "_kioskforge_staging"
    overlay = generate_overlay(cfg, staging, compose_source=compose_source)
    target = boot_mount / OVERLAY_DIR
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(overlay), str(target))

    hook_src = staging / FIRSTRUN_HOOK
    hook_dest = boot_mount / FIRSTRUN_HOOK
    if hook_src.exists():
        shutil.move(str(hook_src), str(hook_dest))

    firstrun = boot_mount / "firstrun.sh"
    hook_line = f'[ -x /boot/firmware/{FIRSTRUN_HOOK} ] && /boot/firmware/{FIRSTRUN_HOOK}\n'
    if firstrun.exists():
        content = firstrun.read_text()
        if FIRSTRUN_HOOK not in content:
            firstrun.write_text(content.rstrip() + "\n" + hook_line)
    else:
        firstrun.write_text("#!/bin/bash\nset -e\n" + hook_line)
        firstrun.chmod(firstrun.stat().st_mode | stat.S_IXUSR)

    readme = staging / "README.inject.md"
    if readme.exists():
        shutil.move(str(readme), str(boot_mount / "README.kioskforge.md"))

    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)

    return target
