from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


@dataclass
class SerialDevice:
    symlink: str
    usb_serial: str
    group: str = "dialout"
    mode: str = "0660"


@dataclass
class DockerConfig:
    enabled: bool = False
    working_dir: str = "/home/kiosk/app"
    compose_filename: str = "docker-compose.yml"


@dataclass
class TailscaleConfig:
    enabled: bool = False


@dataclass
class KioskConfig:
    url: str
    urls: list[str] = field(default_factory=list)
    tab_rotate_seconds: int = 0
    display: str = "wayland"
    username: str = "pi"
    hostname: str = "kiosk"
    hostname_from_mac: bool = False
    disable_screen_blank: bool = True
    hide_cursor: bool = True
    chromium_flags: list[str] = field(default_factory=list)
    firewall: FirewallConfig | None = None
    first_boot_wizard: bool = False
    read_only_root: bool = False
    ssh_password_auth: bool = False
    ssh_port: int | None = None
    packages: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    post_install: list[str] = field(default_factory=list)
    docker: DockerConfig = field(default_factory=DockerConfig)
    tailscale: TailscaleConfig = field(default_factory=TailscaleConfig)
    serial_devices: list[SerialDevice] = field(default_factory=list)
    display_hdmi: dict[str, Any] | None = None


@dataclass
class FirewallConfig:
    enabled: bool = True
    allow_ssh: bool = True
    allow_outbound: bool = True
    allow_ports: list[int] = field(default_factory=list)
    allow_interfaces: list[str] = field(default_factory=list)


DEFAULT_CHROMIUM_FLAGS = [
    "--kiosk",
    "--noerrdialogs",
    "--disable-infobars",
    "--no-first-run",
    "--disable-session-crashed-bubble",
    "--disable-translate",
    "--check-for-update-interval=31536000",
    "--start-maximized",
]


def _mapping(raw: dict, key: str) -> dict:
    value = raw.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"'{key}' must be a mapping")
    return value


def load_config(path: Path) -> KioskConfig:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping")

    kiosk = raw.get("kiosk", raw)
    if not isinstance(kiosk, dict):
        raise ConfigError("'kiosk' section must be a mapping")

    url = kiosk.get("url")
    urls = list(kiosk.get("urls") or [])
    if url:
        urls = [url, *urls]
    if not urls:
        raise ConfigError("Set kiosk.url or kiosk.urls")

    for entry in urls:
        if not isinstance(entry, str) or not entry.startswith(("http://", "https://")):
            raise ConfigError(f"Invalid kiosk URL: {entry!r}")

    tab_rotate = int(kiosk.get("tab_rotate_seconds", 0))
    if tab_rotate < 0:
        raise ConfigError("tab_rotate_seconds must be >= 0")

    display = str(kiosk.get("display", "wayland")).lower()
    if display not in {"wayland", "x11"}:
        raise ConfigError("display must be 'wayland' or 'x11'")

    fw_raw = raw.get("firewall")
    firewall = None
    if fw_raw is not None:
        if not isinstance(fw_raw, dict):
            raise ConfigError("'firewall' must be a mapping")
        firewall = FirewallConfig(
            enabled=bool(fw_raw.get("enabled", True)),
            allow_ssh=bool(fw_raw.get("allow_ssh", True)),
            allow_outbound=bool(fw_raw.get("allow_outbound", True)),
            allow_ports=[int(p) for p in fw_raw.get("allow_ports", [])],
            allow_interfaces=[str(i) for i in fw_raw.get("allow_interfaces", [])],
        )

    system = _mapping(raw, "system")
    docker_raw = _mapping(raw, "docker")
    tailscale_raw = _mapping(raw, "tailscale")

    flags = kiosk.get("chromium_flags") or DEFAULT_CHROMIUM_FLAGS
    if not isinstance(flags, list):
        raise ConfigError("chromium_flags must be a list")

    packages = raw.get("packages") or []
    if not isinstance(packages, list):
        raise ConfigError("packages must be a list")

    env = raw.get("env") or {}
    if not isinstance(env, dict):
        raise ConfigError("env must be a mapping")

    post_install = raw.get("post_install") or []
    if not isinstance(post_install, list):
        raise ConfigError("post_install must be a list of shell commands")

    serial_devices: list[SerialDevice] = []
    for item in raw.get("serial_devices") or []:
        if not isinstance(item, dict):
            raise ConfigError("Each serial_devices entry must be a mapping")
        serial_devices.append(
            SerialDevice(
                symlink=str(item["symlink"]),
                usb_serial=str(item["usb_serial"]),
                group=str(item.get("group", "dialout")),
                mode=str(item.get("mode", "0660")),
            )
        )

    ssh_port = system.get("ssh_port")
    if ssh_port is not None:
        ssh_port = int(ssh_port)

    hdmi = kiosk.get("hdmi")
    if hdmi is not None and not isinstance(hdmi, dict):
        raise ConfigError("kiosk.hdmi must be a mapping")

    return KioskConfig(
        url=urls[0],
        urls=urls,
        tab_rotate_seconds=tab_rotate,
        display=display,
        username=str(system.get("username", "pi")),
        hostname=str(system.get("hostname", "kiosk")),
        hostname_from_mac=bool(system.get("hostname_from_mac", False)),
        disable_screen_blank=bool(kiosk.get("disable_screen_blank", True)),
        hide_cursor=bool(kiosk.get("hide_cursor", True)),
        chromium_flags=[str(f) for f in flags],
        firewall=firewall,
        first_boot_wizard=bool(raw.get("first_boot_wizard", False)),
        read_only_root=bool(system.get("read_only_root", False)),
        ssh_password_auth=bool(system.get("ssh_password_auth", False)),
        ssh_port=ssh_port,
        packages=[str(p) for p in packages],
        env={str(k): str(v) for k, v in env.items()},
        post_install=[str(c) for c in post_install],
        docker=DockerConfig(
            enabled=bool(docker_raw.get("enabled", False)),
            working_dir=str(docker_raw.get("working_dir", "/home/kiosk/app")),
            compose_filename=str(docker_raw.get("compose_file", "docker-compose.yml")),
        ),
        tailscale=TailscaleConfig(enabled=bool(tailscale_raw.get("enabled", False))),
        serial_devices=serial_devices,
        display_hdmi=hdmi,
    )


def config_summary(cfg: KioskConfig) -> dict[str, Any]:
    return {
        "hostname": cfg.hostname,
        "hostname_from_mac": cfg.hostname_from_mac,
        "username": cfg.username,
        "display": cfg.display,
        "urls": cfg.urls,
        "tab_rotate_seconds": cfg.tab_rotate_seconds,
        "first_boot_wizard": cfg.first_boot_wizard,
        "firewall": cfg.firewall.enabled if cfg.firewall else False,
        "docker": cfg.docker.enabled,
        "tailscale": cfg.tailscale.enabled,
        "serial_devices": [d.symlink for d in cfg.serial_devices],
        "read_only_root": cfg.read_only_root,
        "packages": cfg.packages,
    }
