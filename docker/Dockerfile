# syntax=docker/dockerfile:1.7
FROM ghcr.io/tongyi-mai/mobile_world:latest

# Remove MobileWorld code
RUN rm -rf /app/service/src/mobile_world

# Install GMA
COPY pyproject.toml uv.lock README.md /app/gma/
COPY src /app/gma/src
COPY configs /app/gma/configs
ENV UV_HTTP_TIMEOUT=300
RUN --mount=type=cache,target=/root/.cache/uv cd /app/gma && uv sync

# Overlay our AVD with clean gma_init_state snapshot
ENV AVD_NAME=Pixel_8_API_34_x86_64
COPY docker/${AVD_NAME}.avd /root/.android/avd/${AVD_NAME}.avd
COPY docker/${AVD_NAME}.ini /root/.android/avd/${AVD_NAME}.ini
COPY docker/adb_relay.py /usr/local/bin/adb_relay.py
RUN mkdir -p /root/.android && adb keygen /root/.android/adbkey >/dev/null 2>&1
RUN rm -f "/root/.android/avd/${AVD_NAME}.avd"/*.lock

# App and backend artifacts bundled into GMA.
COPY docker/dev/elementx.apk /app/dev/elementx.apk
COPY docker/dev/tempus.apk /app/dev/tempus.apk
COPY docker/dev/whatsapp-project.tar.gz /app/dev/whatsapp-project.tar.gz
COPY docker/dev/whatsapp-postgres-volume.tar.gz /app/dev/whatsapp-postgres-volume.tar.gz
COPY docker/dev/spotify-project.tar.gz /app/dev/spotify-project.tar.gz
COPY docker/dev/whatsapp-images.tar.gz /app/images/whatsapp-images.tar.gz
COPY docker/dev/navidrome-image.tar.gz /app/images/navidrome-image.tar.gz
COPY docker/dev/mall-deploy.zip /app/dev/mall-deploy.zip
COPY docker/dev/meituan-export.zip /app/dev/meituan-export.zip
COPY docker/dev/xiaoshiliu-offline-deploy.tar.gz /app/dev/xiaoshiliu-offline-deploy.tar.gz
COPY docker/dev/hmdp-export.zip /app/dev/hmdp-export.zip
COPY docker/dev/travel-app-migration-pack.tar.gz /app/dev/travel-app-migration-pack.tar.gz

# Use our entrypoint (cleans lock files to avoid AVD conflicts)
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/start_novnc.sh /usr/local/bin/start_novnc.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/start_novnc.sh

WORKDIR /app/gma

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["entrypoint.sh"]
CMD ["tail", "-f", "/var/log/emulator.log", "/var/log/server.log"]
