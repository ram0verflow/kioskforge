# Kioskforge

Provision a Raspberry Pi as a locked-down kiosk: full-screen Chromium, optional Docker Compose backend, host firewall, and Tailscale for remote access.

Define everything in one YAML file. Flash Pi OS, inject the overlay onto the boot partition, boot once — provisioning runs automatically.

## Stack

| Layer | What Kioskforge configures |
|-------|---------------------------|
| **Display** | Chromium in kiosk mode (Wayland/labwc on Bookworm+, X11 fallback) |
| **Application** | Docker Compose service(s) on localhost, displayed in the browser |
| **Network** | `ufw` firewall — SSH and Tailscale only by default |
| **Remote access** | Tailscale mesh VPN (auth key via environment variable) |
| **Hardware** | USB serial udev aliases for attached devices |
| **Identity** | Hostname, SSH hardening, optional read-only rootfs |

Typical deployment:

```
┌─────────────────────────────────────┐
│  Chromium (kiosk, fullscreen)       │
│  → http://localhost:8080            │
├─────────────────────────────────────┤
│  Docker Compose (your app stack)    │
├─────────────────────────────────────┤
│  ufw  │  Tailscale  │  SSH (key)   │
└─────────────────────────────────────┘
         Raspberry Pi OS
```

## Requirements

- **Host machine** — macOS or Linux, for running the CLI and mounting the SD card
- **Raspberry Pi** — Pi 3 or newer, 1 GB+ RAM
- **Raspberry Pi Imager** — flash [Raspberry Pi OS (64-bit)](https://www.raspberrypi.com/software/) with hostname, user, WiFi, and SSH configured there

## Install

```bash
pip install .
# or
pipx install git+https://github.com/ram0verflow/kioskforge.git
```

## Quick start

```bash
# Validate config
kioskforge validate examples/minimal.yaml

# Preview what first boot will apply
kioskforge plan examples/fleet-edge.yaml

# Flash SD card with Raspberry Pi Imager, mount boot partition, inject
kioskforge inject examples/fleet-edge.yaml \
  --boot-mount /media/$USER/bootfs \
  --compose examples/docker-compose.yml

# Boot the Pi and verify
ssh pi@your-hostname.local journalctl -u kioskforge-firstboot --no-pager
```

## Configuration

```yaml
kiosk:
  url: http://localhost:8080       # shown fullscreen in Chromium
  display: wayland                 # wayland | x11
  tab_rotate_seconds: 0            # rotate tabs if multiple URLs

system:
  hostname: lobby-kiosk
  hostname_from_mac: false         # true → kiosk-a1b2c3 from NIC MAC
  username: pi
  ssh_password_auth: false
  ssh_port: 22
  read_only_root: false

firewall:
  enabled: true
  allow_ssh: true
  allow_interfaces:
    - tailscale0                   # allow all traffic on Tailscale iface

docker:
  enabled: true
  working_dir: /home/pi/kiosk-app
  compose_file: docker-compose.yml

tailscale:
  enabled: true                    # requires KIOSKFORGE_TAILSCALE_AUTHKEY at boot

serial_devices:
  - symlink: ttyDevice1
    usb_serial: "00000001"
    group: dialout
    mode: "0660"

first_boot_wizard: false           # true → interactive hostname/URL on console
packages: [curl]
env:
  APP_ENV: production
post_install:
  - systemctl restart kioskforge-docker
```

### Example compose file

```yaml
# examples/docker-compose.yml
services:
  app:
    image: nginx:alpine
    ports:
      - "8080:80"
    restart: unless-stopped
```

Pass it at inject time with `--compose examples/docker-compose.yml`.

## Commands

| Command | Description |
|---------|-------------|
| `kioskforge validate <config>` | Parse and validate YAML |
| `kioskforge plan <config>` | Show provisioning plan |
| `kioskforge generate <config> -o ./out` | Build overlay directory for manual copy |
| `kioskforge inject <config> -b <boot-mount>` | Write overlay and first-boot hook to SD card |

## How it works

1. **Flash** — Raspberry Pi Imager writes the OS and basic settings (user, WiFi, SSH keys).
2. **Inject** — Kioskforge copies a `kioskforge/` overlay to `/boot/firmware/` and registers a one-shot `firstrun.sh` hook.
3. **First boot** — A systemd oneshot installs packages, applies firewall rules, starts Docker Compose, joins Tailscale, and configures Chromium kiosk autostart.
4. **Done** — The oneshot disables itself. Subsequent boots go straight to the kiosk.

## Security

- Do **not** commit Tailscale auth keys or registry tokens to YAML. Set `KIOSKFORGE_TAILSCALE_AUTHKEY` in the systemd environment or export it before first boot.
- Use Raspberry Pi Imager to configure **SSH public-key auth**; keep `ssh_password_auth: false`.
- The default firewall denies all incoming traffic except SSH and configured interfaces (e.g. `tailscale0`).
- Enable `read_only_root: true` for unattended public deployments to reduce SD card corruption risk.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT — see [LICENSE](LICENSE).
