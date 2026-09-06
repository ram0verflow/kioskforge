# Inject instructions

Target hostname: **{{hostname}}**

## Automatic (recommended)

```bash
kioskforge inject your-config.yaml --boot-mount /path/to/bootfs
```

This writes:

- `/boot/firmware/{{overlay_dir}}/config.json`
- `/boot/firmware/{{overlay_dir}}/scripts/*`
- `/boot/firmware/kioskforge-firstrun.sh`
- appends hook to `/boot/firmware/firstrun.sh`

## Manual

Copy `{{overlay_dir}}/` to `/boot/firmware/{{overlay_dir}}/` and run the firstrun hook on first boot.
