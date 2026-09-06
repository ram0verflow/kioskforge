# Kioskforge

**Declarative Raspberry Pi kiosk provisioning** — a modern, general-purpose replacement for bespoke fleet imagers like `spondulix-imager`.

Flash Raspberry Pi OS with [Raspberry Pi Imager](https://www.raspberrypi.com/software/), inject a config overlay onto the boot partition, boot once. Kioskforge configures Chromium kiosk mode (Wayland/labwc or X11), optional Docker Compose, firewall, serial udev rules, and Tailscale.

## Why this exists

`spondulix-imager` (private, `teamsatosys`) was built for Satosys kiosk fleet deployment circa 2024. It used:

| Original approach | Problem today |
|---|---|
| [packer-arm](https://github.com/mkaczanowski/packer-arm) full image builds | Heavy, slow, QEMU/ARM build chain; hard to maintain |
| DietPi + Bullseye base images | Pi OS Bookworm/Trixie uses **Wayland/labwc**; X11/openbox scripts break |
| `rc.local` first boot | Deprecated; systemd + Imager `firstrun.sh` is standard |
| `chromium-browser` package | Renamed to `chromium` on modern Debian |
| Hardcoded Spondulix Docker images + GHCR tokens | Product-specific; secrets were committed to boot config |
| Packer templates per hardware SKU | Raspberry Pi Imager customization + YAML is enough for most fleets |

**What still had merit:** first-boot wizard for field techs, boot-partition config, kiosk autostart, iptables/ufw, Docker Compose sidecar, udev serial aliases, Tailscale for remote fleet access.

Kioskforge keeps those ideas, drops the product coupling, and targets **post-flash injection** instead of rebuilding `.img` files.

## Install

```bash
pip install .
# or
pipx install git+https://github.com/ram0verflow/kioskforge.git
```

## Quick start

```bash
# 1. Validate config
kioskforge validate examples/minimal.yaml

# 2. See provisioning plan
kioskforge plan examples/minimal.yaml

# 3. Flash Pi OS with Raspberry Pi Imager (set user, WiFi, SSH there)

# 4. Mount boot partition and inject
kioskforge inject examples/minimal.yaml --boot-mount /Volumes/bootfs

# 5. Boot the Pi
ssh pi@kiosk.local 'journalctl -u kioskforge-firstboot --no-pager'
```

## Example config

```yaml
kiosk:
  url: https://dashboard.example.com
  display: wayland          # wayland (Pi OS Bookworm+) or x11
  tab_rotate_seconds: 30      # optional multi-tab rotation

system:
  hostname: lobby-kiosk
  hostname_from_mac: false  # true → kiosk-a1b2c3 from NIC MAC
  username: pi
  ssh_password_auth: false
  ssh_port: 22

firewall:
  enabled: true
  allow_ssh: true
  allow_interfaces: [tailscale0]

docker:
  enabled: true
  working_dir: /home/pi/kiosk-app
  compose_file: docker-compose.yml

tailscale:
  enabled: true             # set KIOSKFORGE_TAILSCALE_AUTHKEY on first boot

serial_devices:
  - symlink: ttyDevice1
    usb_serial: "00000001"

first_boot_wizard: true       # interactive URL/hostname on console
packages: [curl]
```

Inject with Docker Compose bundle:

```bash
kioskforge inject examples/fleet-edge.yaml \
  --boot-mount /media/$USER/bootfs \
  --compose examples/docker-compose.yml
```

## Commands

| Command | Description |
|---------|-------------|
| `kioskforge validate <config>` | Parse and validate YAML |
| `kioskforge plan <config>` | Show what first boot will apply |
| `kioskforge generate <config> -o ./out` | Build overlay directory (manual copy) |
| `kioskforge inject <config> -b <boot-mount>` | Write overlay + `firstrun.sh` hook |

## Migration from spondulix-imager

| spondulix-imager | kioskforge |
|---|---|
| `rpi_image.json` / `pi_image.json` (Packer) | Flash with Raspberry Pi Imager + `kioskforge inject` |
| `/boot/spondulix_config` with secrets | Never put secrets in git; use Imager SSH keys + env vars |
| `setup_wizard.sh` (Satosys branded) | `first_boot_wizard: true` (generic) |
| `docker-compose.yml` → ghcr.io/teamsatosys/* | Your own compose file via `--compose` |
| `99-com.rules` ttyCoin/ttyBill | `serial_devices:` in YAML |
| `iptable-rules.sh` | `firewall:` section (ufw) |
| DietPi chromium autostart | Wayland labwc autostart (Bookworm+) |

## Security notes

- **Rotate any secrets** that were ever in `spondulix_config` (Tailscale keys, GitHub PATs).
- Pass Tailscale auth keys at runtime via `KIOSKFORGE_TAILSCALE_AUTHKEY` — not in YAML committed to git.
- Use Raspberry Pi Imager for SSH public-key auth instead of password login.

## Development

```bash
cd kioskforge
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT — see [LICENSE](LICENSE).

## Credits

Evolved from the Satosys Spondulix kiosk fleet tooling. Repackaged as general-purpose open source by [ram0verflow](https://github.com/ram0verflow).
