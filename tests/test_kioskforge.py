import json
from pathlib import Path

import pytest

from kioskforge.config import ConfigError, load_config
from kioskforge.generator import chromium_command, generate_overlay


def test_load_minimal_example():
    cfg = load_config(Path(__file__).parent.parent / "examples" / "minimal.yaml")
    assert cfg.url == "https://example.com/dashboard"
    assert cfg.display == "wayland"
    assert cfg.firewall is not None
    assert cfg.firewall.enabled is True


def test_requires_url():
    with pytest.raises(ConfigError):
        load_config(Path(__file__).parent / "fixtures" / "empty.yaml")


def test_generate_overlay(tmp_path: Path):
    cfg = load_config(Path(__file__).parent.parent / "examples" / "minimal.yaml")
    overlay = generate_overlay(cfg, tmp_path)
    assert overlay.is_dir()
    config = json.loads((overlay / "config.json").read_text())
    assert config["urls"] == ["https://example.com/dashboard"]
    assert (overlay / "scripts" / "apply-kiosk.sh").exists()
    assert (tmp_path / "kioskforge-firstrun.sh").exists()


def test_chromium_command():
    cfg = load_config(Path(__file__).parent.parent / "examples" / "minimal.yaml")
    cmd = chromium_command(cfg)
    assert "https://example.com/dashboard" in cmd
    assert "--kiosk" in cmd
