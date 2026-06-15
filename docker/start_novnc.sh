#!/usr/bin/env bash
set -euo pipefail

NOVNC_DIR=${NOVNC_DIR:-/usr/share/novnc}
WEBSOCKIFY=${WEBSOCKIFY:-/usr/share/novnc/utils/novnc_proxy}
DISPLAY_ID=${DISPLAY_ID:-:0}
VNC_RESOLUTION=${VNC_RESOLUTION:-1920x1080x24}

export DISPLAY="${DISPLAY_ID}"

DISPLAY_NUM="${DISPLAY_ID#:}"
if ! pgrep -x Xvfb >/dev/null 2>&1; then
    rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}" 2>/dev/null || true
fi

Xvfb "${DISPLAY_ID}" -screen 0 "${VNC_RESOLUTION}" >/var/log/xvfb.log 2>&1 &

echo "[GMA] Waiting for Xvfb..."
for _ in $(seq 1 30); do
    if [ -S "/tmp/.X11-unix/X${DISPLAY_ID#:}" ] && xset -display "${DISPLAY_ID}" q >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

if command -v dbus-launch >/dev/null 2>&1; then
    dbus-launch openbox >/var/log/openbox.log 2>&1 &
else
    openbox >/var/log/openbox.log 2>&1 &
fi

echo "[GMA] Waiting for window manager..."
for _ in $(seq 1 30); do
    if xprop -root _NET_SUPPORTING_WM_CHECK >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

x11vnc -display "${DISPLAY_ID}" -forever -shared -rfbport 5900 -nopw -quiet \
    >/var/log/x11vnc.log 2>&1 &

"${WEBSOCKIFY}" --vnc localhost:5900 --listen 0.0.0.0:5800 --web "${NOVNC_DIR}" \
    >/var/log/novnc.log 2>&1 &

echo "[GMA] noVNC running at http://0.0.0.0:5800/vnc.html"
