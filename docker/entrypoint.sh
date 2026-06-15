#!/bin/bash
# GMA container entrypoint

# Disable IPv6 (fixes emulator SIM card issue)
sysctl net.ipv6.conf.all.disable_ipv6=1 2>/dev/null || true

# Start Docker-in-Docker (for app backends)
start-docker.sh 2>/dev/null &
sleep 5

# Load app backend Docker images if present
if [ -d /app/images ]; then
    cd /app/images
    for f in *.tar *.tar.gz; do [ -f "$f" ] && docker load -i "$f"; done
fi

# --- Start Android Emulator ---
echo "[GMA] Starting Android emulator..."

if [ "${ENABLE_VNC:-false}" = "true" ] || [ "${ENABLE_VNC:-false}" = "1" ]; then
    echo "[GMA] Starting noVNC display on port 5800..."
    /usr/local/bin/start_novnc.sh
fi

# Clean stale lock files from the AVD (left over from snapshot creation)
AVD_DIR="/root/.android/avd/${AVD_NAME}.avd"
rm -f "${AVD_DIR}"/*.lock /tmp/avd/running/*.ini 2>/dev/null || true

# Kill any existing emulators
adb devices 2>/dev/null | grep emulator | cut -f1 | while read dev; do
    adb -s "$dev" emu kill 2>/dev/null || true
done

EMU_OPTS="-no-audio -no-snapshot -gpu swiftshader_indirect"
if [ "${ENABLE_VNC:-false}" = "true" ] || [ "${ENABLE_VNC:-false}" = "1" ]; then
    export DISPLAY=:0
    nohup emulator -avd "${AVD_NAME}" ${EMU_OPTS} > /var/log/emulator.log 2>&1 &
else
    nohup emulator -avd "${AVD_NAME}" -no-window ${EMU_OPTS} > /var/log/emulator.log 2>&1 &
fi

# Wait for boot
TIMEOUT=${EMULATOR_TIMEOUT:-600}
START=$(date +%s)
while true; do
    RESULT=$(adb shell getprop sys.boot_completed 2>&1)
    if [ "$RESULT" = "1" ]; then
        echo "[GMA] Emulator booted"
        break
    fi
    ELAPSED=$(( $(date +%s) - START ))
    if [ $ELAPSED -gt $TIMEOUT ]; then
        echo "[GMA] ERROR: Emulator boot timed out after ${TIMEOUT}s"
        echo "[GMA] Emulator log:"
        cat /var/log/emulator.log
        exit 1
    fi
    sleep 5
done

# Disable animations
adb shell "settings put global window_animation_scale 0.0" || true
adb shell "settings put global transition_animation_scale 0.0" || true
adb shell "settings put global animator_duration_scale 0.0" || true

adb root || true
sleep 2
adb shell ime set com.android.adbkeyboard/.AdbIME 2>/dev/null || true

# Expose ADB externally
python3 /usr/local/bin/adb_relay.py >/var/log/adb-relay.log 2>&1 &

# --- Start GMA Device Proxy ---
echo "[GMA] Starting device proxy on port 8000..."
cd /app/gma
if [ -x ./.venv/bin/gma ]; then
    ./.venv/bin/gma server --port 8000 >> /var/log/server.log 2>&1 &
else
    uv run gma server --port 8000 >> /var/log/server.log 2>&1 &
fi

echo "[GMA] Container ready"

# Keep container alive
exec "$@"
