#!/bin/bash
# Run only after full power-on, before starting any other PL/HDMI/Reader program.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
test -f final_frame_retire_fclk1_125.bit
test -f final_frame_retire_fclk1_125.hwh
HDMI_UI_BOOT_ID=$(cat /proc/sys/kernel/random/boot_id)
python3 -u 01_load_identity.py --cold-boot "$HDMI_UI_BOOT_ID"
exec python3 -u 11_live_ui_touch.py --boot "$HDMI_UI_BOOT_ID" --cold-session-confirmed
