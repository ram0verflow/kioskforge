#!/bin/bash
# Runs once from Raspberry Pi OS firstrun.sh (boot partition).
set -euo pipefail

BOOT="/boot/firmware"
OVERLAY="${BOOT}/{{overlay_dir}}"
UNIT_SRC="${OVERLAY}/systemd/{{systemd_unit}}"
UNIT_DEST="/etc/systemd/system/{{systemd_unit}}"

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "kioskforge: missing unit at $UNIT_SRC" >&2
  exit 1
fi

cp "$UNIT_SRC" "$UNIT_DEST"
chmod 644 "$UNIT_DEST"
systemctl daemon-reload
systemctl enable --now "{{systemd_unit}}"

rm -f "${BOOT}/{{overlay_dir}}/../kioskforge-firstrun.sh" 2>/dev/null || true
rm -f "${BOOT}/kioskforge-firstrun.sh" 2>/dev/null || true
