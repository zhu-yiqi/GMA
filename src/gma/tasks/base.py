"""Base task interface.

Tasks declare metadata (goal, apps, tags, snapshot) as class attributes,
implement ``setup()`` for initialization, and return evaluation criteria
from ``criteria()``.  The framework handles snapshot loading, app cleanup,
scoring aggregation, and teardown.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import Any

from loguru import logger

from gma.evaluation.criteria import Criterion
from gma.evaluation.result import EvalResult, aggregate_results


FIXED_EMULATOR_DATE_SPEC = "100100002026.00"  # 2026-10-01 00:00:00 UTC
FIXED_EMULATOR_TIMEZONE = "UTC"
WEBAPP_PACKAGES = (
    "gma.webapp.hmdp",
    "gma.webapp.meituan",
    "gma.webapp.mall",
    "gma.webapp.xiaoshiliu",
    "gma.webapp.travel",
)
GALLERY_PACKAGE = "gallery.photomanager.picturegalleryapp.imagegallery"
GALLERY_MEDIA_PERMISSIONS = (
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.ACCESS_MEDIA_LOCATION",
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
    "android.permission.READ_EXTERNAL_STORAGE",
)
GALLERY_MEDIA_APPOPS = (
    "READ_MEDIA_IMAGES",
    "READ_MEDIA_VIDEO",
    "READ_MEDIA_VISUAL_USER_SELECTED",
    "READ_EXTERNAL_STORAGE",
)


def _clear_android_packages(client, packages: tuple[str, ...], *, reason: str) -> None:
    """Best-effort local app-state reset for packages with backend-backed data."""
    for package in packages:
        try:
            client.shell(
                f"am force-stop {package} >/dev/null 2>&1 || true; "
                f"pm clear {package} >/dev/null 2>&1 || true"
            )
        except Exception:
            logger.warning(f"{package} cache cleanup failed during {reason}")


def _grant_gallery_media_permissions(client, *, reason: str) -> None:
    """Keep seeded Gallery files visible after Gallery app data is cleared."""
    commands = [
        f"pm grant {GALLERY_PACKAGE} {permission} >/dev/null 2>&1 || true"
        for permission in GALLERY_MEDIA_PERMISSIONS
    ]
    commands.extend(
        f"appops set {GALLERY_PACKAGE} {appop} allow >/dev/null 2>&1 || true"
        for appop in GALLERY_MEDIA_APPOPS
    )
    try:
        client.shell("; ".join(commands))
    except Exception:
        logger.warning(f"Gallery media permission grant failed during {reason}")


class BaseTask(ABC):
    """Abstract base class for all benchmark tasks."""

    # --- Declarative metadata (set as class attributes) ---

    goal: str                   # What the agent should accomplish
    apps: set[str] = set()     # App names involved in this task
    tags: set[str] = set()     # Tags for filtering (e.g. "lang-en")
    snapshot: str = "gma_ready_state"  # Snapshot to load before setup
    assets: tuple[Any, ...] = ()    # Declarative task data to seed after reset
    user_interaction: str | None = None  # Optional call_user response contract
    user_simulation: dict[str, Any] | str | None = None  # Legacy call_user contract

    def __init__(self, params: dict[str, Any] | None = None):
        self.params = params or {}

    @property
    def name(self) -> str:
        return self.__class__.__name__

    # --- Lifecycle methods ---

    def setup(self, client) -> None:
        """Task-specific initialization (inject SMS, push files, etc.).

        Called after the snapshot is loaded and app cleanup runs.
        ``client`` is a ``GMAClient`` (or ``AndroidController``).
        Override as needed — default is a no-op.
        """
        pass

    @abstractmethod
    def criteria(self) -> list[Criterion]:
        """Return the evaluation criteria for this task."""
        ...

    def teardown(self, client) -> None:
        """Task-specific cleanup. Override as needed."""
        pass

    # --- Evaluation ---

    def evaluate(self, client) -> EvalResult:
        """Evaluate this task against the current device state.

        Default: evaluate all criteria and aggregate via weighted average.
        Override for fully custom evaluation logic.
        """
        criteria = self.criteria()
        if not criteria:
            logger.warning(f"Task {self.name} returned no criteria")
            return EvalResult(score=0.0)
        results = []
        for criterion in criteria:
            try:
                result = criterion.evaluate(client)
                results.append(result)
            except Exception as e:
                logger.error(f"Criterion {criterion.name} failed: {e}")
                results.append(criterion._fail(f"Exception: {e}"))
        return aggregate_results(results)

    # --- Full lifecycle (called by the runner) ---

    def initialize(self, client) -> bool:
        """Full initialization: shared reset -> declarative assets -> setup.

        Returns True on success, False on failure.
        """
        from gma.assets import apply_assets

        try:
            if hasattr(client, "reset_terminal_state"):
                client.reset_terminal_state()

            if not prepare_task_environment(
                client,
                snapshot=self.snapshot,
                apps=self.apps,
            ):
                return False

            if self.assets:
                logger.info(f"Applying {len(self.assets)} asset(s) for {self.name}")
                apply_assets(client, list(self.assets), task=self)

            logger.info(f"Running setup for {self.name}")
            self.setup(client)
            try:
                client.press_home()
            except Exception as e:
                logger.warning(f"Failed to return home after {self.name} initialization: {e}")
            return True
        except Exception as e:
            logger.error(f"Task {self.name} initialization failed: {e}")
            return False

    def finalize(self, client) -> None:
        """Full teardown. Called after evaluation."""
        try:
            self.teardown(client)
        except Exception as e:
            logger.error(f"Task {self.name} teardown failed: {e}")
        logger.info(f"Task {self.name} finalized")


def _wait_for_device_ready(client, timeout: float = 90.0) -> bool:
    """Wait until ADB can talk to the emulator after snapshot/load transitions."""
    deadline = time.time() + timeout
    device = getattr(client, "device", "emulator-5554")
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            if hasattr(client, "exec"):
                client.exec(
                    f"adb -s {device} wait-for-device >/dev/null 2>&1 && "
                    f"adb -s {device} shell wm size >/dev/null",
                    timeout=15,
                )
            else:
                client.shell("wm size >/dev/null")
            return True
        except Exception as e:
            last_error = e
            time.sleep(2)
    logger.error(f"Device {device} did not become ready after snapshot transition: {last_error}")
    return False


def _set_fixed_emulator_time(client) -> None:
    """Pin reset/task-start emulator time to a deterministic UTC timestamp."""
    device = getattr(client, "device", "emulator-5554")
    command = f"""
set -eu
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell settings put global auto_time 0 >/dev/null 2>&1 || true
adb -s {device} shell settings put global auto_time_zone 0 >/dev/null 2>&1 || true
adb -s {device} shell setprop persist.sys.timezone {FIXED_EMULATOR_TIMEZONE} >/dev/null 2>&1 || true
adb -s {device} shell date -u {FIXED_EMULATOR_DATE_SPEC} >/dev/null
"""
    try:
        if hasattr(client, "exec"):
            client.exec(command, timeout=30)
        else:
            client.shell("settings put global auto_time 0 >/dev/null 2>&1 || true")
            client.shell("settings put global auto_time_zone 0 >/dev/null 2>&1 || true")
            client.shell(f"setprop persist.sys.timezone {FIXED_EMULATOR_TIMEZONE} >/dev/null 2>&1 || true")
            client.shell(f"date -u {FIXED_EMULATOR_DATE_SPEC} >/dev/null")
    except Exception as e:
        logger.warning(f"Failed to set fixed emulator time: {e}")


def load_snapshot_state_status(client, snapshot: str = "gma_init_state") -> dict[str, Any]:
    """Load a named emulator snapshot and report whether it was actually loaded."""
    if not snapshot:
        return {"ok": True, "snapshot": snapshot, "loaded_snapshot": False, "used_live_state": True}
    logger.info(f"Loading snapshot: {snapshot}")
    if client.load_snapshot(snapshot, log_error=snapshot != "gma_ready_state"):
        if not _wait_for_device_ready(client):
            return {"ok": False, "snapshot": snapshot, "loaded_snapshot": False, "used_live_state": False}
        _set_fixed_emulator_time(client)
        return {"ok": True, "snapshot": snapshot, "loaded_snapshot": True, "used_live_state": False}

    if snapshot == "gma_ready_state":
        logger.info(
            "gma_ready_state snapshot unavailable; preparing the live emulator "
            "without loading gma_init_state"
        )
        if not _wait_for_device_ready(client):
            return {"ok": False, "snapshot": snapshot, "loaded_snapshot": False, "used_live_state": False}
        _set_fixed_emulator_time(client)
        try:
            client.press_home()
        except Exception as e:
            logger.warning(f"Failed to return home after missing ready snapshot: {e}")
        return {"ok": True, "snapshot": snapshot, "loaded_snapshot": False, "used_live_state": True}

    logger.error(f"Failed to load snapshot: {snapshot}")
    return {"ok": False, "snapshot": snapshot, "loaded_snapshot": False, "used_live_state": False}


def load_snapshot_state(client, snapshot: str = "gma_init_state") -> bool:
    """Load a named emulator snapshot. Returns True if environment setup can continue."""
    return bool(load_snapshot_state_status(client, snapshot=snapshot)["ok"])


def clear_environment(client, apps: set[str] | None = None) -> bool:
    """Clear app/backend drift on top of the currently loaded snapshot."""
    from gma.apps import cleanup_all

    logger.info("Clearing environment state")
    requested_apps = set(apps or [])

    def requested(*names: str) -> bool:
        return not requested_apps or bool(requested_apps & set(names))

    try:
        # Some apps retain local UI/cache state even when the restored
        # snapshot does not contain the underlying user-visible data.
        critical_cleanup_failed = False

        if requested("Messages"):
            client.shell("pm clear com.google.android.apps.messaging")
        if requested("Clock"):
            client.shell("pm clear com.google.android.deskclock")
        if requested("Gallery"):
            client.shell(f"pm clear {GALLERY_PACKAGE}")
            _grant_gallery_media_permissions(client, reason="reset")

        if requested("Mail"):
            client.shell("pm clear com.gmailclone")

        if requested("Mall", "MallAdmin"):
            try:
                client.shell("pm uninstall --user 0 com.testmall.app >/dev/null 2>&1 || true")
            except Exception:
                logger.warning("Stale testmall app uninstall failed during reset")

        webapp_packages = []
        if requested("HMDP"):
            webapp_packages.append("gma.webapp.hmdp")
        if requested("Meituan"):
            webapp_packages.append("gma.webapp.meituan")
        if requested("Mall", "MallAdmin"):
            webapp_packages.append("gma.webapp.mall")
        if requested("XiaoShiLiu", "Xiaoshiliu", "xiaoshiliu"):
            webapp_packages.append("gma.webapp.xiaoshiliu")
        if requested("Travel"):
            webapp_packages.append("gma.webapp.travel")
        if webapp_packages:
            _clear_android_packages(client, tuple(webapp_packages), reason="reset")

        # DeskClock seeds two default alarm templates on first launch, so
        # force one launch, scrub the DB, then stop the app again.
        if requested("Clock"):
            try:
                client.exec(
                    "adb -s emulator-5554 shell monkey -p com.google.android.deskclock "
                    "-c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 && "
                    "sleep 2 && "
                    "adb -s emulator-5554 pull "
                    "/data/user_de/0/com.google.android.deskclock/databases/alarms.db "
                    "/tmp/alarms_reset.db >/dev/null 2>&1 && "
                    "python3 -c 'import sqlite3; "
                    "conn=sqlite3.connect(\"/tmp/alarms_reset.db\"); "
                    "conn.execute(\"DELETE FROM alarm_instances\"); "
                    "conn.execute(\"DELETE FROM alarm_templates\"); "
                    "conn.commit()' && "
                    "adb -s emulator-5554 push /tmp/alarms_reset.db "
                    "/data/user_de/0/com.google.android.deskclock/databases/alarms.db >/dev/null 2>&1 && "
                    "adb -s emulator-5554 shell am force-stop com.google.android.deskclock"
                )
            except Exception:
                logger.warning("Clock alarm database cleanup failed during reset")

        # Gallery can retain thumbnail/media metadata even after pm clear.
        if requested("Gallery"):
            try:
                client.shell(
                    "rm -rf /sdcard/Pictures/.thumbnails /sdcard/DCIM/.thumbnails 2>/dev/null || true"
                )
                client.shell(
                    "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Pictures || true"
                )
                client.shell(
                    "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM || true"
                )
            except Exception:
                logger.warning("Gallery metadata cleanup failed during reset")

        # The system Files app may reject pm clear, so clean shared storage
        # directly and then force-stop the app as a best-effort reset.
        if requested("Clock", "Files", "Gallery", "Mail"):
            storage_dirs = []
            if requested("Clock"):
                storage_dirs.append("/sdcard/Alarms")
            if requested("Gallery"):
                storage_dirs.extend(("/sdcard/DCIM", "/sdcard/Movies", "/sdcard/Pictures"))
            if requested("Files"):
                storage_dirs.extend(("/sdcard/Documents", "/sdcard/Download"))
            if requested("Mail"):
                storage_dirs.append("/sdcard/Android/data/com.gmailclone")
            try:
                for storage_dir in dict.fromkeys(storage_dirs):
                    try:
                        client.shell(
                            f"find {storage_dir} -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +"
                        )
                    except Exception:
                        pass
            except Exception:
                logger.warning("Shared storage cleanup failed during reset")
        if requested("Files", "Gallery"):
            try:
                client.shell("pm clear com.google.android.providers.media.module")
            except Exception:
                logger.warning("pm clear com.google.android.providers.media.module failed")

        if requested("Files"):
            try:
                client.shell("pm clear com.google.android.documentsui")
            except Exception:
                logger.warning("pm clear com.google.android.documentsui failed; using force-stop only")
                client.shell("am force-stop com.google.android.documentsui")

        if requested("ElementX"):
            try:
                from gma.apps.elementx import clear_elementx_user_state

                clear_elementx_user_state(client)
            except Exception:
                logger.warning("ElementX backend room cleanup failed during reset")
                critical_cleanup_failed = True

        if requested("Tempus"):
            try:
                from gma.apps.tempus import reset_tempus_backend

                reset_tempus_backend(client)
            except Exception:
                logger.warning("Tempus backend reset failed during reset")
                critical_cleanup_failed = True

        if requested("Mattermost"):
            try:
                client.exec(
                    "adb -s emulator-5554 root >/dev/null 2>&1 || true && "
                    "adb -s emulator-5554 shell rm -f "
                    "/data/user/0/com.mattermost.rnbeta/files/databases/aHR0cDovLzEwLjAuMi4yOjgwNjU=.db "
                    "/data/user/0/com.mattermost.rnbeta/app_webview/Default/Cookies "
                    "/data/user/0/com.mattermost.rnbeta/app_webview/Default/Cookies-journal "
                    "/data/user/0/com.mattermost.rnbeta/cache/logs/* "
                    "/data/user/0/com.mattermost.rnbeta/cache/image_manager_disk_cache/* "
                    "2>/dev/null || true && "
                    "adb -s emulator-5554 pull "
                    "/data/user/0/com.mattermost.rnbeta/files/databases/app.db "
                    "/tmp/mattermost_app.db >/dev/null 2>&1 && "
                    "sqlite3 /tmp/mattermost_app.db \"DELETE FROM Servers; "
                    "INSERT INTO Servers (id, _changed, _status, db_path, display_name, identifier, last_active_at, url) VALUES ("
                    "'QdIvSvS8U9xnwy51', 0, 'created', "
                    "'file:///data/user/0/com.mattermost.rnbeta/files//databases/aHR0cDovLzEwLjAuMi4yOjgwNjU=.db', "
                    "'Company', 'mattermost-server', 0, 'http://10.0.2.2:8065');\" && "
                    "adb -s emulator-5554 push /tmp/mattermost_app.db "
                    "/data/user/0/com.mattermost.rnbeta/files/databases/app.db >/dev/null 2>&1 && "
                    "adb -s emulator-5554 shell chown u0_a195:u0_a195 "
                    "/data/user/0/com.mattermost.rnbeta/files/databases/app.db >/dev/null 2>&1"
                )
                client.shell("am force-stop com.mattermost.rnbeta")
            except Exception:
                logger.warning("Mattermost local app cache cleanup failed during reset")

            try:
                from gma.apps.mattermost import reset_mattermost_backend

                reset_mattermost_backend(client)
            except Exception:
                logger.warning("Mattermost backend reset failed during reset")
                critical_cleanup_failed = True

        if requested("Mastodon"):
            try:
                from gma.assets.apply import (
                    clear_mastodon_app_cache,
                    reset_mastodon_backend,
                    sync_mastodon_app_state,
                )

                reset_mastodon_backend(client)
                clear_mastodon_app_cache(client)
                sync_mastodon_app_state(client)
            except Exception:
                logger.warning("Mastodon backend/app reset failed during reset")
                critical_cleanup_failed = True
        else:
            try:
                from gma.assets.apply import sync_mastodon_app_state

                sync_mastodon_app_state(client)
            except Exception:
                logger.warning("Mastodon app token refresh failed during reset")

        if requested("Mall", "MallAdmin"):
            try:
                from gma.apps.offline_webapps import reset_mall_backend

                reset_mall_backend(client)
            except Exception:
                logger.warning("Mall backend reset failed during reset")
                critical_cleanup_failed = True

        if requested("Meituan"):
            try:
                from gma.apps.offline_webapps import reset_meituan_backend

                reset_meituan_backend(client)
            except Exception:
                logger.warning("Meituan backend reset failed during reset")
                critical_cleanup_failed = True

        if requested("XiaoShiLiu", "Xiaoshiliu", "xiaoshiliu"):
            try:
                from gma.apps.offline_webapps import reset_xiaoshiliu_backend

                reset_xiaoshiliu_backend(client)
            except Exception:
                logger.warning("XiaoShiLiu backend reset failed during reset")
                critical_cleanup_failed = True

        if requested("HMDP"):
            try:
                from gma.apps.offline_webapps import reset_hmdp_backend

                reset_hmdp_backend(client)
            except Exception:
                logger.warning("HMDP backend reset failed during reset")
                critical_cleanup_failed = True

        if requested("Travel"):
            try:
                from gma.apps.offline_webapps import reset_travel_backend

                reset_travel_backend(client)
            except Exception:
                logger.warning("Travel backend reset failed during reset")
                critical_cleanup_failed = True

        if critical_cleanup_failed:
            return False

        cleanup_all(client)
        logger.info("Environment clear complete")
        return True
    except Exception as e:
        logger.error(f"Environment clear failed: {e}")
        return False


def reset_backend_state(client, apps: set[str] | None = None) -> bool:
    """Reset backend-visible data and app caches that can outlive backend resets.

    This is the fast path for `gma env reset`: the Android snapshot already
    restores local app storage, so most system apps do not need full cleanup.
    Backend-backed apps still get targeted cache clears where stale local state
    can otherwise disagree with the reset backend.
    """
    logger.info("Resetting backend state")
    requested_apps = set(apps or [])

    def requested(*names: str) -> bool:
        return not requested_apps or bool(requested_apps & set(names))

    try:
        if requested("ElementX"):
            from gma.apps.elementx import reset_elementx_backend

            reset_elementx_backend(client)

        if requested("Tempus"):
            from gma.apps.tempus import reset_tempus_backend

            reset_tempus_backend(client)

        if requested("Mattermost"):
            from gma.apps.mattermost import reset_mattermost_backend

            reset_mattermost_backend(client)

        if requested("Mastodon"):
            from gma.assets.apply import (
                clear_mastodon_app_cache,
                reset_mastodon_backend,
                sync_mastodon_app_state,
            )

            reset_mastodon_backend(client)
            clear_mastodon_app_cache(client)
            # This refreshes the Android account DB directly; it is not a UI login.
            sync_mastodon_app_state(client)

        if requested("Mall", "MallAdmin"):
            from gma.apps.offline_webapps import reset_mall_backend

            _clear_android_packages(client, ("gma.webapp.mall",), reason="backend reset")
            reset_mall_backend(client)

        if requested("Meituan"):
            from gma.apps.offline_webapps import reset_meituan_backend

            _clear_android_packages(client, ("gma.webapp.meituan",), reason="backend reset")
            reset_meituan_backend(client)

        if requested("XiaoShiLiu", "Xiaoshiliu", "xiaoshiliu"):
            from gma.apps.offline_webapps import reset_xiaoshiliu_backend

            _clear_android_packages(client, ("gma.webapp.xiaoshiliu",), reason="backend reset")
            reset_xiaoshiliu_backend(client)

        if requested("HMDP"):
            from gma.apps.offline_webapps import reset_hmdp_backend

            _clear_android_packages(client, ("gma.webapp.hmdp",), reason="backend reset")
            reset_hmdp_backend(client)

        if requested("Travel"):
            from gma.apps.offline_webapps import reset_travel_backend

            _clear_android_packages(client, ("gma.webapp.travel",), reason="backend reset")
            reset_travel_backend(client)

        logger.info("Backend state reset complete")
        return True
    except Exception as e:
        logger.error(f"Backend state reset failed: {e}")
        return False


def repair_loaded_snapshot_shell_state(client) -> bool:
    """Apply cheap Android-side ready-state fixes after loading gma_ready_state."""
    try:
        _configure_chrome_for_webapps(client)
    except Exception as e:
        logger.warning(f"Failed to configure Chrome for web apps: {e}")

    try:
        _ensure_ready_state_launcher_icons(client)
    except Exception as e:
        logger.warning(f"Failed to repair ready-state launcher icons: {e}")

    _set_fixed_emulator_time(client)
    for package in (
        "com.mattermost.rnbeta",
        "io.element.android.x",
        "com.eddyizm.tempus.debug",
        "org.joinmastodon.android.mastodon",
        "gma.webapp.mall",
        "gma.webapp.meituan",
        "gma.webapp.xiaoshiliu",
        "gma.webapp.hmdp",
        "gma.webapp.travel",
    ):
        try:
            client.shell(f"am force-stop {package} >/dev/null 2>&1 || true")
        except Exception:
            logger.warning(f"Failed to force-stop {package} after fast reset")
    try:
        client.press_home()
    except Exception as e:
        logger.warning(f"Failed to return to home after fast ready-state repair: {e}")
    return True


def _configure_chrome_for_webapps(client) -> None:
    """Keep Chrome web-app launches off the emulator's unstable Vulkan path."""
    from gma.apps._shell import run_bash

    run_bash(
        client,
        r"""
set -euo pipefail
DEVICE=emulator-5554
adb -s "$DEVICE" root >/dev/null 2>&1 || true
adb -s "$DEVICE" shell "printf '%s\n' 'chrome --disable-vulkan --disable-features=Vulkan --unsafely-treat-insecure-origin-as-secure=http://101.37.229.242:8050,http://101.37.229.242:8040,http://101.37.229.242:8030,http://101.37.229.242:8070,http://101.37.229.242:8060,http://10.0.2.2:8050,http://10.0.2.2:8040,http://10.0.2.2:8030,http://10.0.2.2:8070,http://10.0.2.2:8060' > /data/local/tmp/chrome-command-line" >/dev/null 2>&1 || true
adb -s "$DEVICE" shell am force-stop com.android.chrome >/dev/null 2>&1 || true
""",
        timeout=30,
    )


def _ensure_ready_state_launcher_icons(client) -> None:
    """Pin reset-time installed apps back onto the Pixel Launcher home screen."""
    from gma.apps._shell import run_bash

    run_bash(
        client,
        r"""
set -euo pipefail
DEVICE=emulator-5554
DB=/data/data/com.google.android.apps.nexuslauncher/databases/launcher_4_by_5.db
TMP=/tmp/gma_launcher_ready.db

adb -s "$DEVICE" root >/dev/null 2>&1 || true
# Chrome is used for the offline web apps. Disable Vulkan because Chromium
# can crash this nested emulator with kvm_user_backed_ram_map failures.
adb -s "$DEVICE" shell "printf '%s\n' 'chrome --disable-vulkan --disable-features=Vulkan --unsafely-treat-insecure-origin-as-secure=http://101.37.229.242:8050,http://101.37.229.242:8040,http://101.37.229.242:8030,http://101.37.229.242:8070,http://101.37.229.242:8060,http://10.0.2.2:8050,http://10.0.2.2:8040,http://10.0.2.2:8030,http://10.0.2.2:8070,http://10.0.2.2:8060' > /data/local/tmp/chrome-command-line" >/dev/null 2>&1 || true
adb -s "$DEVICE" shell am force-stop com.android.chrome >/dev/null 2>&1 || true

install_apk_if_missing() {
  local package="$1"
  local apk_name="$2"
  if adb -s "$DEVICE" shell pm path "$package" >/dev/null 2>&1; then
    return 0
  fi
  local apk="/app/dev/$apk_name"
  if [ ! -f "$apk" ]; then
    apk="/app/mobileworld/$apk_name"
  fi
  if [ -f "$apk" ]; then
    adb -s "$DEVICE" install -r -g "$apk" >/dev/null
  fi
}

install_apk_if_missing io.element.android.x elementx.apk
install_apk_if_missing com.eddyizm.tempus.debug tempus.apk

install_meituan_webview_wrapper() {
  local package="gma.webapp.meituan"
  local work="/tmp/gma_meituan_wrapper"
  local sdk="/opt/android-sdk"
  local bt="$sdk/build-tools/34.0.0"
  local android_jar="$sdk/platforms/android-34/android.jar"
  rm -rf "$work"
  mkdir -p "$work/src/gma/webapp/meituan" "$work/res/drawable" "$work/res/values" "$work/gen" "$work/classes" "$work/dex"
  cat > "$work/AndroidManifest.xml" <<\XML
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="gma.webapp.meituan">
    <uses-sdk android:minSdkVersion="23" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:theme="@style/AppTheme" android:label="Meituan" android:icon="@drawable/ic_launcher" android:resizeableActivity="true" android:allowBackup="false" android:supportsRtl="true" android:usesCleartextTraffic="true" android:hardwareAccelerated="false">
        <activity android:name=".MainActivity" android:exported="true" android:windowSoftInputMode="adjustResize" android:hardwareAccelerated="false">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
XML
  cat > "$work/res/values/styles.xml" <<\XML
<resources>
    <style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar">
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowActionBar">false</item>
        <item name="android:colorAccent">#ff6600</item>
    </style>
</resources>
XML
  cat > "$work/res/drawable/ic_launcher.xml" <<\XML
<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="48dp" android:height="48dp" android:viewportWidth="48" android:viewportHeight="48">
    <path android:fillColor="#ff6600" android:pathData="M8,4h32v40H8z" />
    <path android:fillColor="#ffffff" android:pathData="M15,12h18v4H15zM15,20h18v4H15zM15,28h13v4H15z" />
</vector>
XML
  cat > "$work/src/gma/webapp/meituan/MainActivity.java" <<\JAVA
package gma.webapp.meituan;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.webkit.JsPromptResult;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

public class MainActivity extends Activity {
    private static final String URL = "http://10.0.2.2:8050/meituan/";
    private static final String DEFAULT_USERNAME = "owner";
    private static final String DEFAULT_PASSWORD = "123456";
    private static final String PREFS_NAME = "gma_login";
    private WebView webView;

    private void applyLoginExtras(Intent intent) {
        if (intent == null) {
            return;
        }
        SharedPreferences.Editor editor = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit();
        boolean changed = false;
        String username = intent.getStringExtra("gma_username");
        String password = intent.getStringExtra("gma_password");
        if (username != null && username.length() > 0) {
            editor.putString("username", username);
            changed = true;
        }
        if (password != null && password.length() > 0) {
            editor.putString("password", password);
            changed = true;
        }
        if (changed) {
            editor.apply();
        }
    }

    private String loginValue(String key, String fallback) {
        return getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(key, fallback);
    }

    private String jsString(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '\\': out.append("\\\\"); break;
                case '"': out.append("\\\""); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 32 || c > 126) {
                        String hex = Integer.toHexString(c);
                        out.append("\\u");
                        for (int j = hex.length(); j < 4; j++) {
                            out.append('0');
                        }
                        out.append(hex);
                    } else {
                        out.append(c);
                    }
            }
        }
        out.append("\"");
        return out.toString();
    }

    private void injectFocusedInputText(String text) {
        if (webView == null || text.length() == 0) {
            return;
        }
        String quoted = jsString(text);
        String script = "(function(){"
            + "const el=document.activeElement;"
            + "if(!el||!(/^(INPUT|TEXTAREA)$/i.test(el.tagName)||el.isContentEditable))return false;"
            + "const text=" + quoted + ";"
            + "if(el.isContentEditable){document.execCommand('insertText',false,text);return true;}"
            + "const value=el.value||'';"
            + "const start=el.selectionStart==null?value.length:el.selectionStart;"
            + "const end=el.selectionEnd==null?start:el.selectionEnd;"
            + "el.value=value.slice(0,start)+text+value.slice(end);"
            + "const pos=start+text.length;"
            + "if(el.setSelectionRange)el.setSelectionRange(pos,pos);"
            + "let ev;try{ev=new InputEvent('input',{bubbles:true,inputType:'insertText',data:text});}catch(e){ev=new Event('input',{bubbles:true});}"
            + "el.dispatchEvent(ev);return true;"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    private void deleteFocusedInputText() {
        if (webView == null) {
            return;
        }
        String script = "(function(){"
            + "const el=document.activeElement;"
            + "if(!el||!(/^(INPUT|TEXTAREA)$/i.test(el.tagName)||el.isContentEditable))return false;"
            + "if(el.isContentEditable){document.execCommand('delete',false,null);return true;}"
            + "const value=el.value||'';"
            + "let start=el.selectionStart==null?value.length:el.selectionStart;"
            + "let end=el.selectionEnd==null?start:el.selectionEnd;"
            + "if(start===end&&start>0)start-=1;"
            + "el.value=value.slice(0,start)+value.slice(end);"
            + "if(el.setSelectionRange)el.setSelectionRange(start,start);"
            + "let ev;try{ev=new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward',data:null});}catch(e){ev=new Event('input',{bubbles:true});}"
            + "el.dispatchEvent(ev);return true;"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    private void dispatchFocusedInputEnter() {
        if (webView == null) {
            return;
        }
        String script = "(function(){"
            + "const el=document.activeElement;"
            + "if(!el||!(/^(INPUT|TEXTAREA)$/i.test(el.tagName)||el.isContentEditable))return false;"
            + "const opts={key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true,cancelable:true};"
            + "el.dispatchEvent(new KeyboardEvent('keydown',opts));"
            + "el.dispatchEvent(new KeyboardEvent('keyup',opts));return true;"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    private String textForKeyEvent(KeyEvent event) {
        int unicode = event.getUnicodeChar();
        if (unicode > 0) {
            return Character.toString((char) unicode);
        }
        int keyCode = event.getKeyCode();
        if (keyCode >= KeyEvent.KEYCODE_A && keyCode <= KeyEvent.KEYCODE_Z) {
            char c = (char) ('a' + (keyCode - KeyEvent.KEYCODE_A));
            return Character.toString(c);
        }
        if (keyCode >= KeyEvent.KEYCODE_0 && keyCode <= KeyEvent.KEYCODE_9) {
            char c = (char) ('0' + (keyCode - KeyEvent.KEYCODE_0));
            return Character.toString(c);
        }
        switch (keyCode) {
            case KeyEvent.KEYCODE_SPACE: return " ";
            case KeyEvent.KEYCODE_PERIOD: return ".";
            case KeyEvent.KEYCODE_COMMA: return ",";
            case KeyEvent.KEYCODE_MINUS: return "-";
            case KeyEvent.KEYCODE_EQUALS: return "=";
            case KeyEvent.KEYCODE_SLASH: return "/";
            case KeyEvent.KEYCODE_BACKSLASH: return "\\";
            case KeyEvent.KEYCODE_SEMICOLON: return ";";
            case KeyEvent.KEYCODE_APOSTROPHE: return "'";
            case KeyEvent.KEYCODE_LEFT_BRACKET: return "[";
            case KeyEvent.KEYCODE_RIGHT_BRACKET: return "]";
            case KeyEvent.KEYCODE_GRAVE: return "`";
            default: return null;
        }
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN && webView != null) {
            int keyCode = event.getKeyCode();
            if (keyCode == KeyEvent.KEYCODE_DEL) {
                deleteFocusedInputText();
                return true;
            }
            if (keyCode == KeyEvent.KEYCODE_ENTER) {
                dispatchFocusedInputEnter();
                return true;
            }
            String text = textForKeyEvent(event);
            if (text != null) {
                injectFocusedInputText(text);
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private void hydrateCart() {
        if (webView == null) {
            return;
        }
        String username = jsString(loginValue("username", DEFAULT_USERNAME));
        String password = jsString(loginValue("password", DEFAULT_PASSWORD));
        String script = "(async()=>{"
            + "try{const u=" + username + ";const password=" + password + ";"
            + "const r=await fetch(\"/api/admin/user_login\",{method:\"POST\",credentials:\"include\",headers:{\"Content-Type\":\"application/json\"},body:JSON.stringify({username:u,password})});"
            + "const p=await r.json();if(p.status===200){localStorage.setItem(\"mt-username\",u);}"
            + "const c=await fetch(\"/api/v1/gma_cart?username=\"+encodeURIComponent(u),{credentials:\"include\"});"
            + "const cp=await c.json();if(cp&&cp.status===200&&cp.data){const next=JSON.stringify(cp.data);"
            + "if(localStorage.getItem(\"cartList\")!==next){localStorage.setItem(\"cartList\",next);if(sessionStorage.getItem(\"gma-cart-reloaded\")!==next){sessionStorage.setItem(\"gma-cart-reloaded\",next);location.reload();}}}"
            + "if(!location.hash||location.hash===\"#/login\") location.hash=\"#/home\";"
            + "}catch(e){console.error(e);}"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        applyLoginExtras(getIntent());
        WebView.setWebContentsDebuggingEnabled(true);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        webView = new WebView(this);
        webView.setLayerType(View.LAYER_TYPE_SOFTWARE, null);
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        webView.requestFocus();
        setContentView(webView);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        webView.clearCache(true);
        webView.clearFormData();
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                hydrateCart();
            }
        });
        webView.loadUrl(URL);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        applyLoginExtras(intent);
        if (webView != null) {
            hydrateCart();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                @Override
                public void run() {
                    hydrateCart();
                }
            }, 500);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
JAVA
  "$bt/aapt" package -f -m -J "$work/gen" -M "$work/AndroidManifest.xml" -S "$work/res" -I "$android_jar" >/dev/null
  javac -encoding UTF-8 -source 1.8 -target 1.8 -bootclasspath "$android_jar" -d "$work/classes" $(find "$work/src" "$work/gen" -name "*.java") >/dev/null
  "$bt/d8" --min-api 23 --output "$work/dex" $(find "$work/classes" -name "*.class") >/dev/null
  "$bt/aapt" package -f -M "$work/AndroidManifest.xml" -S "$work/res" -I "$android_jar" -F "$work/unsigned.apk" >/dev/null
  (cd "$work/dex" && "$bt/aapt" add "$work/unsigned.apk" classes.dex >/dev/null)
  if [ ! -f /tmp/gma_debug.keystore ]; then
    keytool -genkeypair -v -keystore /tmp/gma_debug.keystore -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >/dev/null
  fi
  "$bt/zipalign" -f 4 "$work/unsigned.apk" "$work/aligned.apk" >/dev/null
  "$bt/apksigner" sign --ks /tmp/gma_debug.keystore --ks-pass pass:android --key-pass pass:android --out /tmp/gma-meituan-launcher.apk "$work/aligned.apk" >/dev/null
  adb -s "$DEVICE" install -r /tmp/gma-meituan-launcher.apk >/dev/null
}


install_simple_webview_wrapper() {
  local package="$1"
  local label="$2"
  local url="$3"
  local accent="$4"
  local login_mode="$5"
  local version_code="${6:-}"
  local version_name="${7:-}"
  local version_attrs=""
  local safe_name="${package//./_}"
  local package_path="${package//.//}"
  local work="/tmp/${safe_name}_wrapper"
  local sdk="/opt/android-sdk"
  local bt="$sdk/build-tools/34.0.0"
  local android_jar="$sdk/platforms/android-34/android.jar"
  if [ -n "$version_code" ]; then
    version_attrs="${version_attrs} android:versionCode=\"$version_code\""
  fi
  if [ -n "$version_name" ]; then
    version_attrs="${version_attrs} android:versionName=\"$version_name\""
  fi
  rm -rf "$work"
  mkdir -p "$work/src/$package_path" "$work/res/drawable" "$work/res/values" "$work/gen" "$work/classes" "$work/dex"
  cat > "$work/AndroidManifest.xml" <<XML
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="$package"$version_attrs>
    <uses-sdk android:minSdkVersion="23" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:theme="@style/AppTheme" android:label="$label" android:icon="@drawable/ic_launcher" android:resizeableActivity="true" android:allowBackup="false" android:supportsRtl="true" android:usesCleartextTraffic="true" android:hardwareAccelerated="false">
        <activity android:name=".MainActivity" android:exported="true" android:windowSoftInputMode="adjustResize" android:hardwareAccelerated="false">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
XML
  cat > "$work/res/values/styles.xml" <<XML
<resources>
    <style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar">
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowActionBar">false</item>
        <item name="android:colorAccent">$accent</item>
    </style>
</resources>
XML
  cat > "$work/res/drawable/ic_launcher.xml" <<XML
<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="48dp" android:height="48dp" android:viewportWidth="48" android:viewportHeight="48">
    <path android:fillColor="$accent" android:pathData="M24,4a20,20 0,1 0,0.1,0z" />
    <path android:fillColor="#ffffff" android:pathData="M14,15h20v4H14zM14,23h20v4H14zM14,31h14v4H14z" />
</vector>
XML
  cat > "$work/src/$package_path/MainActivity.java" <<'JAVA'
package __GMA_PACKAGE__;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.webkit.JsPromptResult;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

public class MainActivity extends Activity {
    private static final String URL = "__GMA_URL__";
    private static final String LOGIN_MODE = "__GMA_LOGIN_MODE__";
    private static final String PREFS_NAME = "gma_login";
    private static final int FILE_CHOOSER_REQUEST = 4101;
    private WebView webView;
    private ValueCallback<Uri[]> filePathCallback;

    private void applyLoginExtras(Intent intent) {
        if (intent == null) {
            return;
        }
        SharedPreferences.Editor editor = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit();
        boolean changed = false;
        String username = intent.getStringExtra("gma_username");
        String userId = intent.getStringExtra("gma_user_id");
        String phone = intent.getStringExtra("gma_phone");
        String password = intent.getStringExtra("gma_password");
        if (username != null && username.length() > 0) {
            editor.putString("username", username);
            changed = true;
        }
        if (userId != null && userId.length() > 0) {
            editor.putString("user_id", userId);
            changed = true;
        }
        if (phone != null && phone.length() > 0) {
            editor.putString("phone", phone);
            changed = true;
        }
        if (password != null && password.length() > 0) {
            editor.putString("password", password);
            changed = true;
        }
        if (changed) {
            editor.apply();
        }
    }

    private String loginValue(String key, String fallback) {
        return getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(key, fallback);
    }

    private String jsString(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '\\': out.append("\\\\"); break;
                case '"': out.append("\\\""); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 32 || c > 126) {
                        String hex = Integer.toHexString(c);
                        out.append("\\u");
                        for (int j = hex.length(); j < 4; j++) {
                            out.append('0');
                        }
                        out.append(hex);
                    } else {
                        out.append(c);
                    }
            }
        }
        out.append("\"");
        return out.toString();
    }

    private void injectFocusedInputText(String text) {
        if (webView == null || text.length() == 0) {
            return;
        }
        String quoted = jsString(text);
        String script = "(function(){"
            + "const el=document.activeElement;"
            + "if(!el||!(/^(INPUT|TEXTAREA)$/i.test(el.tagName)||el.isContentEditable))return false;"
            + "const text=" + quoted + ";"
            + "if(el.isContentEditable){document.execCommand('insertText',false,text);return true;}"
            + "const value=el.value||'';"
            + "const start=el.selectionStart==null?value.length:el.selectionStart;"
            + "const end=el.selectionEnd==null?start:el.selectionEnd;"
            + "el.value=value.slice(0,start)+text+value.slice(end);"
            + "const pos=start+text.length;"
            + "if(el.setSelectionRange)el.setSelectionRange(pos,pos);"
            + "let ev;try{ev=new InputEvent('input',{bubbles:true,inputType:'insertText',data:text});}catch(e){ev=new Event('input',{bubbles:true});}"
            + "el.dispatchEvent(ev);return true;"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    private void deleteFocusedInputText() {
        if (webView == null) {
            return;
        }
        String script = "(function(){"
            + "const el=document.activeElement;"
            + "if(!el||!(/^(INPUT|TEXTAREA)$/i.test(el.tagName)||el.isContentEditable))return false;"
            + "if(el.isContentEditable){document.execCommand('delete',false,null);return true;}"
            + "const value=el.value||'';"
            + "let start=el.selectionStart==null?value.length:el.selectionStart;"
            + "let end=el.selectionEnd==null?start:el.selectionEnd;"
            + "if(start===end&&start>0)start-=1;"
            + "el.value=value.slice(0,start)+value.slice(end);"
            + "if(el.setSelectionRange)el.setSelectionRange(start,start);"
            + "let ev;try{ev=new InputEvent('input',{bubbles:true,inputType:'deleteContentBackward',data:null});}catch(e){ev=new Event('input',{bubbles:true});}"
            + "el.dispatchEvent(ev);return true;"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    private void dispatchFocusedInputEnter() {
        if (webView == null) {
            return;
        }
        String script = "(function(){"
            + "const el=document.activeElement;"
            + "if(!el||!(/^(INPUT|TEXTAREA)$/i.test(el.tagName)||el.isContentEditable))return false;"
            + "const opts={key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true,cancelable:true};"
            + "el.dispatchEvent(new KeyboardEvent('keydown',opts));"
            + "el.dispatchEvent(new KeyboardEvent('keyup',opts));return true;"
            + "})()";
        webView.evaluateJavascript(script, null);
    }

    private String textForKeyEvent(KeyEvent event) {
        int unicode = event.getUnicodeChar();
        if (unicode > 0) {
            return Character.toString((char) unicode);
        }
        int keyCode = event.getKeyCode();
        if (keyCode >= KeyEvent.KEYCODE_A && keyCode <= KeyEvent.KEYCODE_Z) {
            char c = (char) ('a' + (keyCode - KeyEvent.KEYCODE_A));
            return Character.toString(c);
        }
        if (keyCode >= KeyEvent.KEYCODE_0 && keyCode <= KeyEvent.KEYCODE_9) {
            char c = (char) ('0' + (keyCode - KeyEvent.KEYCODE_0));
            return Character.toString(c);
        }
        switch (keyCode) {
            case KeyEvent.KEYCODE_SPACE: return " ";
            case KeyEvent.KEYCODE_PERIOD: return ".";
            case KeyEvent.KEYCODE_COMMA: return ",";
            case KeyEvent.KEYCODE_MINUS: return "-";
            case KeyEvent.KEYCODE_EQUALS: return "=";
            case KeyEvent.KEYCODE_SLASH: return "/";
            case KeyEvent.KEYCODE_BACKSLASH: return "\\";
            case KeyEvent.KEYCODE_SEMICOLON: return ";";
            case KeyEvent.KEYCODE_APOSTROPHE: return "'";
            case KeyEvent.KEYCODE_LEFT_BRACKET: return "[";
            case KeyEvent.KEYCODE_RIGHT_BRACKET: return "]";
            case KeyEvent.KEYCODE_GRAVE: return "`";
            default: return null;
        }
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if ("mall".equals(LOGIN_MODE) || "travel".equals(LOGIN_MODE)) {
            return super.dispatchKeyEvent(event);
        }
        if (event.getAction() == KeyEvent.ACTION_DOWN && webView != null) {
            int keyCode = event.getKeyCode();
            if (keyCode == KeyEvent.KEYCODE_DEL) {
                deleteFocusedInputText();
                return true;
            }
            if (keyCode == KeyEvent.KEYCODE_ENTER) {
                dispatchFocusedInputEnter();
                return true;
            }
            String text = textForKeyEvent(event);
            if (text != null) {
                injectFocusedInputText(text);
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private void ensureLogin() {
        if (webView == null) {
            return;
        }
        String script;
        if ("xiaoshiliu".equals(LOGIN_MODE)) {
            script = "(()=>{"
                + "try{const home='http://10.0.2.2:8030/';"
                + "if(localStorage.getItem('token')&&location.href.indexOf('/login')>=0)location.replace(home);"
                + "}catch(e){console.error(e);}"
                + "})()";
        } else if ("mall".equals(LOGIN_MODE)) {
            String username = jsString(loginValue("username", "owner"));
            String password = jsString(loginValue("password", "123456"));
            script = "(async()=>{try{"
                + "const username=" + username + ";const password=" + password + ";const marker='GMA-Mall-Seed-User';const reloadKey='GMA-Mall-Login-Reloaded-'+username;"
                + "for(let i=0;i<40;i++){if(window.uni&&typeof window.uni.setStorageSync==='function')break;await new Promise(r=>setTimeout(r,250));}"
                + "const body=new URLSearchParams({username,password});"
                + "const r=await fetch('/mall/app/api/sso/login',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded;charset=utf-8'},body});"
                + "const p=await r.json();if(p&&p.code===200&&p.data){const token=p.data.tokenHead+p.data.token;localStorage.setItem('token',token);localStorage.setItem('username',username);localStorage.setItem('password',password);"
                + "if(window.uni&&typeof window.uni.setStorageSync==='function'){window.uni.setStorageSync('token',token);window.uni.setStorageSync('username',username);window.uni.setStorageSync('password',password);}"
                + "const vr=await fetch('/mall/app/api/sso/info',{headers:{Authorization:token}});const vp=await vr.json();if(vp&&vp.code===200&&vp.data){localStorage.setItem('userInfo',JSON.stringify(vp.data));localStorage.setItem(marker,username);if(window.uni&&typeof window.uni.setStorageSync==='function'){window.uni.setStorageSync('userInfo',vp.data);}}"
                + "if(location.hash&&location.hash!=='#/pages/login/login'&&sessionStorage.getItem(reloadKey)!=='1'){sessionStorage.setItem(reloadKey,'1');location.reload();return;}}"
                + "if(!location.hash||location.hash==='#/pages/login/login') location.href='http://10.0.2.2:8040/#/pages/user/user';"
                + "}catch(e){console.error(e);}})()";
        } else if ("travel".equals(LOGIN_MODE)) {
            String login = jsString(loginValue("username", "owner@example.com"));
            String password = jsString(loginValue("password", "123456"));
            script = "(async()=>{try{"
                + "const login=" + login + ";const password=" + password + ";const marker='GMA-Travel-Seed-User';const home='http://10.0.2.2:8060/trip/user/profile';"
                + "const session=await fetch('/trip/api/auth/session',{cache:'no-store'}).then(r=>r.json()).catch(()=>null);"
                + "if(session&&session.user&&session.user.email===login){localStorage.setItem(marker,login);if(location.href.indexOf('/user/login')>=0)location.replace(home);return;}"
                + "const csrf=await fetch('/trip/api/auth/csrf',{cache:'no-store'}).then(r=>r.json()).catch(()=>null);"
                + "if(!csrf||!csrf.csrfToken)return;"
                + "const body=new URLSearchParams({csrfToken:csrf.csrfToken,login,password,redirect:'false',callbackUrl:home});"
                + "await fetch('/trip/api/auth/callback/credentials',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded;charset=utf-8'},body});"
                + "const verified=await fetch('/trip/api/auth/session',{cache:'no-store'}).then(r=>r.json()).catch(()=>null);"
                + "if(verified&&verified.user&&verified.user.email===login){localStorage.setItem(marker,login);if(location.href.indexOf('/user/login')>=0||location.pathname==='/trip'||location.pathname==='/trip/')location.replace(home);}"
                + "}catch(e){console.error(e);}})()";
        } else if ("hmdp".equals(LOGIN_MODE)) {
            String phone = jsString(loginValue("phone", "13810246820"));
            script = "(async()=>{try{"
                + "const phone=" + phone + ";const marker='GMA-HMDP-Seed-Phone';const home='http://10.0.2.2:8070/hmdp/';"
                + "const raw=localStorage.getItem('Hmdp-User');"
                + "if(localStorage.getItem(marker)===phone&&raw){if(location.href.indexOf('/login')>=0||location.href.indexOf('/register')>=0)location.href=home;return;}"
                + "const cr=await fetch('/hmdp/api/user/code?phone='+encodeURIComponent(phone),{method:'POST'});"
                + "const cp=await cr.json();const code=(cp&&cp.data)||'123456';"
                + "const lr=await fetch('/hmdp/api/user/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone,code})});"
                + "const lp=await lr.json();if(lp&&lp.success!==false&&lp.data){localStorage.setItem('Hmdp-User',JSON.stringify({token:String(lp.data),userInfo:{}}));localStorage.setItem(marker,phone);location.replace(home);return;}"
                + "if(location.href.indexOf('/login')>=0||location.href.indexOf('/register')>=0) location.href=home;"
                + "}catch(e){console.error(e);}})()";
        } else {
            script = "void 0";
        }
        webView.evaluateJavascript(script, null);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        applyLoginExtras(getIntent());
        WebView.setWebContentsDebuggingEnabled(true);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        webView = new WebView(this);
        webView.setLayerType(View.LAYER_TYPE_SOFTWARE, null);
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        webView.requestFocus();
        setContentView(webView);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                Intent intent = null;
                try {
                    intent = params.createIntent();
                } catch (Exception ignored) {
                    intent = null;
                }
                if (intent == null) {
                    intent = new Intent(Intent.ACTION_GET_CONTENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("image/*");
                }
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                    return true;
                } catch (Exception e) {
                    filePathCallback = null;
                    callback.onReceiveValue(null);
                    return false;
                }
            }

            @Override
            public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, final JsPromptResult result) {
                final EditText input = new EditText(MainActivity.this);
                input.setSingleLine(true);
                input.setText(defaultValue == null ? "" : defaultValue);
                input.setSelectAllOnFocus(true);
                final AlertDialog dialog = new AlertDialog.Builder(MainActivity.this)
                    .setTitle(message == null || message.length() == 0 ? "Input" : message)
                    .setView(input)
                    .setPositiveButton(android.R.string.ok, new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface dialogInterface, int which) {
                            result.confirm(input.getText().toString());
                        }
                    })
                    .setNegativeButton(android.R.string.cancel, new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface dialogInterface, int which) {
                            result.cancel();
                        }
                    })
                    .create();
                dialog.setOnCancelListener(new DialogInterface.OnCancelListener() {
                    @Override
                    public void onCancel(DialogInterface dialogInterface) {
                        result.cancel();
                    }
                });
                dialog.setOnShowListener(new DialogInterface.OnShowListener() {
                    @Override
                    public void onShow(DialogInterface dialogInterface) {
                        input.requestFocus();
                        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                        if (imm != null) {
                            imm.showSoftInput(input, InputMethodManager.SHOW_IMPLICIT);
                        }
                    }
                });
                dialog.show();
                return true;
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                ensureLogin();
            }
        });
        webView.loadUrl(URL);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        applyLoginExtras(intent);
        if (webView != null) {
            ensureLogin();
        }
    }

    private Uri[] fileChooserUrisFromIntent(int resultCode, Intent data) {
        if (resultCode != RESULT_OK || data == null) {
            return null;
        }
        Uri[] parsed = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
        if (parsed != null && parsed.length > 0) {
            return parsed;
        }
        ClipData clipData = data.getClipData();
        if (clipData != null && clipData.getItemCount() > 0) {
            Uri[] uris = new Uri[clipData.getItemCount()];
            for (int i = 0; i < clipData.getItemCount(); i++) {
                uris[i] = clipData.getItemAt(i).getUri();
            }
            return uris;
        }
        Uri dataUri = data.getData();
        if (dataUri != null) {
            return new Uri[] { dataUri };
        }
        return null;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST) {
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(fileChooserUrisFromIntent(resultCode, data));
                filePathCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                @Override
                public void run() {
                    ensureLogin();
                }
            }, 500);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
JAVA
  python3 - "$work/src/$package_path/MainActivity.java" "$package" "$url" "$login_mode" <<'PYVARS'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("__GMA_PACKAGE__", sys.argv[2])
text = text.replace("__GMA_URL__", sys.argv[3])
text = text.replace("__GMA_LOGIN_MODE__", sys.argv[4])
path.write_text(text)
PYVARS
  "$bt/aapt" package -f -m -J "$work/gen" -M "$work/AndroidManifest.xml" -S "$work/res" -I "$android_jar" >/dev/null
  javac -encoding UTF-8 -source 1.8 -target 1.8 -bootclasspath "$android_jar" -d "$work/classes" $(find "$work/src" "$work/gen" -name "*.java") >/dev/null
  "$bt/d8" --min-api 23 --output "$work/dex" $(find "$work/classes" -name "*.class") >/dev/null
  "$bt/aapt" package -f -M "$work/AndroidManifest.xml" -S "$work/res" -I "$android_jar" -F "$work/unsigned.apk" >/dev/null
  (cd "$work/dex" && "$bt/aapt" add "$work/unsigned.apk" classes.dex >/dev/null)
  if [ ! -f /tmp/gma_debug.keystore ]; then
    keytool -genkeypair -v -keystore /tmp/gma_debug.keystore -storepass android -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >/dev/null
  fi
  "$bt/zipalign" -f 4 "$work/unsigned.apk" "$work/aligned.apk" >/dev/null
  "$bt/apksigner" sign --ks /tmp/gma_debug.keystore --ks-pass pass:android --key-pass pass:android --out "/tmp/${safe_name}.apk" "$work/aligned.apk" >/dev/null
  adb -s "$DEVICE" install -r "/tmp/${safe_name}.apk" >/dev/null
}

install_meituan_webview_wrapper
install_simple_webview_wrapper gma.webapp.xiaoshiliu XiaoShiLiu http://10.0.2.2:8030/ "#e91e63" xiaoshiliu
install_simple_webview_wrapper gma.webapp.mall Mall http://10.0.2.2:8040/ "#1976d2" mall
install_simple_webview_wrapper gma.webapp.hmdp HMDP http://10.0.2.2:8070/hmdp/ "#ff6a00" hmdp 1 0.0.1-SNAPSHOT
install_simple_webview_wrapper gma.webapp.travel Travel http://10.0.2.2:8060/trip "#009688" travel


if ! adb -s "$DEVICE" shell test -f "$DB"; then
  exit 0
fi
owner=$(adb -s "$DEVICE" shell stat -c '%u:%g' "$DB" 2>/dev/null | tr -d '\r' || true)
adb -s "$DEVICE" pull "$DB" "$TMP" >/dev/null
python3 - <<'PY2'
from __future__ import annotations

import sqlite3
import subprocess

DB = "/tmp/gma_launcher_ready.db"
DEVICE = "emulator-5554"
APPS = [
    ("Mall", "gma.webapp.mall", -100, 0, 0, 1, 0),
    ("Meituan", "gma.webapp.meituan", -100, 0, 1, 1, 0),
    ("XiaoShiLiu", "gma.webapp.xiaoshiliu", -100, 0, 2, 1, 0),
    ("HMDP", "gma.webapp.hmdp", -100, 0, 3, 1, 0),
    ("Mattermost", "com.mattermost.rnbeta", -100, 0, 0, 2, 0),
    ("Element X", "io.element.android.x", -100, 0, 1, 2, 0),
    ("Tempus", "com.eddyizm.tempus.debug", -100, 0, 2, 2, 0),
    ("Mastodon", "org.joinmastodon.android.mastodon", -100, 0, 3, 2, 0),
    ("Clock", "com.google.android.deskclock", -100, 0, 0, 3, 0),
    ("Calendar", "org.fossify.calendar", -100, 0, 1, 3, 0),
    ("Travel", "gma.webapp.travel", -100, 0, 2, 3, 0),
    ("Mail", "com.gmailclone", -100, 0, 3, 3, 0),
    ("Files", "com.google.android.documentsui", -100, 0, 0, 4, 0),
    ("Gallery", "gallery.photomanager.picturegalleryapp.imagegallery", -100, 0, 1, 4, 0),
    ("Contacts", "com.google.android.contacts", -100, 0, 2, 4, 0),
    ("OpenDocument Reader", "at.tomtasche.reader", -100, 0, 3, 4, 0),
    ("Settings", "com.android.settings", -100, 1, 0, 1, 0),
    ("Camera", "com.android.camera2", -100, 1, 1, 1, 0),
    ("Maps", "com.google.android.apps.maps", -100, 1, 2, 1, 0),
]
def chrome_webapp_intent(webapp_id: str, url: str, name: str) -> str:
    return (
        "#Intent;"
        "action=org.chromium.chrome.browser.webapps.WebappManager.ACTION_START_SECURE_WEBAPP;"
        "component=com.android.chrome/org.chromium.chrome.browser.webapps.SecureWebAppLauncher;"
        f"S.org.chromium.chrome.browser.webapp_id={webapp_id};"
        f"S.org.chromium.chrome.browser.webapp_url={url};"
        f"S.org.chromium.chrome.browser.webapp_scope={url};"
        f"S.org.chromium.chrome.browser.webapp_name={name};"
        f"S.org.chromium.chrome.browser.webapp_short_name={name};"
        "i.org.chromium.chrome.browser.webapp_display_mode=3;"
        "i.org.chromium.chrome.browser.webapp_source=12;"
        "end"
    )


WEB_APPS = []


def resolve_component(package: str) -> str | None:
    out = subprocess.run(
        ["adb", "-s", DEVICE, "shell", "cmd", "package", "resolve-activity", "--brief", package],
        check=False,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    for line in reversed(out):
        line = line.strip().replace("\r", "")
        if "/" in line and not line.startswith("priority="):
            return line
    return None


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cols = [row[1] for row in conn.execute("pragma table_info(favorites)")]
template = conn.execute(
    "select * from favorites where itemType = 0 and container = -100 order by _id limit 1"
).fetchone()
if template is None:
    template = conn.execute(
        "select * from favorites where itemType = 0 order by "
        "case when container = -101 then 0 else 1 end, _id limit 1"
    ).fetchone()
if template is None:
    raise SystemExit(0)

next_id = conn.execute("select coalesce(max(_id), 0) + 1 from favorites").fetchone()[0]
conn.execute("delete from favorites where title = ? or intent like ?", ("Meituan", "%gma_meituan%"))
conn.execute("delete from favorites where container = -100 and (title = ? or intent like ?)", ("Messages", "%com.google.android.apps.messaging%"))
for title, package, container, screen, cell_x, cell_y, rank in APPS:
    component = resolve_component(package)
    if not component:
        continue
    intent = (
        "#Intent;action=android.intent.action.MAIN;"
        "category=android.intent.category.LAUNCHER;"
        f"component={component};end"
    )
    conn.execute("delete from favorites where title = ? or intent like ?", (title, f"%{package}%"))
    row = dict(template)
    row.update(
        {
            "_id": next_id,
            "title": title,
            "intent": intent,
            "container": container,
            "screen": screen,
            "cellX": cell_x,
            "cellY": cell_y,
            "spanX": 1,
            "spanY": 1,
            "itemType": 0,
            "appWidgetId": -1,
            "rank": rank,
            "restored": 0,
            "options": 0,
            "modified": 0,
        }
    )
    insert_cols = [col for col in cols if col in row]
    placeholders = ", ".join("?" for _ in insert_cols)
    conn.execute(
        f"insert into favorites ({', '.join(insert_cols)}) values ({placeholders})",
        [row[col] for col in insert_cols],
    )
    next_id += 1

chrome_template = conn.execute(
    "select * from favorites where intent like '%com.android.chrome%' order by case when container = -101 then 0 else 1 end, _id limit 1"
).fetchone()
shortcut_template = chrome_template or template
conn.execute("delete from favorites where intent like ?", ("%com.testmall.app%",))
for title, url, cell_x, cell_y, intent_override in WEB_APPS:
    intent = intent_override or (
        f"{url}#Intent;action=android.intent.action.VIEW;"
        "category=android.intent.category.BROWSABLE;"
        "package=com.android.chrome;end"
    )
    conn.execute("delete from favorites where title = ? or intent like ?", (title, f"%{url}%"))
    row = dict(shortcut_template)
    row.update(
        {
            "_id": next_id,
            "title": title,
            "intent": intent,
            "container": -100,
            "screen": 0,
            "cellX": cell_x,
            "cellY": cell_y,
            "spanX": 1,
            "spanY": 1,
            "itemType": 1,
            "appWidgetId": -1,
            "rank": 0,
            "restored": 0,
            "options": 0,
            "modified": 0,
        }
    )
    insert_cols = [col for col in cols if col in row]
    placeholders = ", ".join("?" for _ in insert_cols)
    conn.execute(
        f"insert into favorites ({', '.join(insert_cols)}) values ({placeholders})",
        [row[col] for col in insert_cols],
    )
    next_id += 1
conn.commit()
conn.close()
PY2
adb -s "$DEVICE" shell am force-stop com.google.android.apps.nexuslauncher >/dev/null 2>&1 || true
adb -s "$DEVICE" push "$TMP" "$DB" >/dev/null
if [ -n "$owner" ]; then
  adb -s "$DEVICE" shell chown "$owner" "$DB" >/dev/null 2>&1 || true
fi
adb -s "$DEVICE" shell chmod 660 "$DB" >/dev/null 2>&1 || true
adb -s "$DEVICE" shell am force-stop com.google.android.apps.nexuslauncher >/dev/null 2>&1 || true
""",
        timeout=60,
    )


def ensure_ready_state_apps(
    client,
    snapshot: str = "gma_ready_state",
    apps: set[str] | None = None,
    bootstrap_apps: bool = True,
) -> bool:
    """Repair app/backend state that a ready snapshot depends on.

    The emulator snapshot restores Android-side state, but some apps still
    depend on live backend/bootstrap steps after the snapshot load.
    """
    if snapshot != "gma_ready_state":
        return True

    from gma.apps.elementx import (
        clear_elementx_user_state,
        repair_elementx_app_state,
        reset_elementx_backend,
        sync_elementx_app_state,
    )
    from gma.apps.hmdp import login_hmdp_app
    from gma.apps.mattermost import repair_mattermost_app_state, sync_mattermost_app_state
    from gma.apps.mall import login_mall_app
    from gma.apps.meituan import login_meituan_app
    from gma.apps.offline_webapps import (
        ensure_hmdp_backend,
        ensure_hmdp_backend_running,
        ensure_mall_backend,
        ensure_mall_backend_running,
        ensure_meituan_backend,
        ensure_meituan_backend_running,
        ensure_xiaoshiliu_backend,
        ensure_xiaoshiliu_backend_running,
        ensure_travel_backend,
        ensure_travel_backend_running,
        reset_hmdp_backend,
        reset_mall_backend,
        reset_meituan_backend,
        reset_xiaoshiliu_backend,
        reset_travel_backend,
    )
    from gma.apps.tempus import repair_tempus_app_state, reset_tempus_backend, sync_tempus_app_state
    from gma.apps.travel import login_travel_app
    from gma.apps.xiaoshiliu import login_xiaoshiliu_app
    from gma.assets.apply import sync_mastodon_app_state

    def reset_and_ensure_elementx(client):
        reset_elementx_backend(client)
        clear_elementx_user_state(client)
        sync_elementx_app_state(client)

    def reset_and_ensure_tempus(client):
        reset_tempus_backend(client)
        sync_tempus_app_state(client)

    def reset_and_ensure_mall(client):
        reset_mall_backend(client)
        _clear_android_packages(client, ("gma.webapp.mall",), reason="ready-state bootstrap")
        login_mall_app(client)

    def reset_and_ensure_meituan(client):
        reset_meituan_backend(client)
        _clear_android_packages(client, ("gma.webapp.meituan",), reason="ready-state bootstrap")
        login_meituan_app(client)

    def reset_and_ensure_xiaoshiliu(client):
        reset_xiaoshiliu_backend(client)
        ensure_xiaoshiliu_backend(client)
        _clear_android_packages(client, ("gma.webapp.xiaoshiliu",), reason="ready-state bootstrap")
        login_xiaoshiliu_app(client)

    def reset_and_ensure_hmdp(client):
        reset_hmdp_backend(client)
        ensure_hmdp_backend(client)
        _clear_android_packages(client, ("gma.webapp.hmdp",), reason="ready-state bootstrap")
        login_hmdp_app(client)

    def reset_and_ensure_travel(client):
        reset_travel_backend(client)
        ensure_travel_backend(client)
        _clear_android_packages(client, ("gma.webapp.travel",), reason="ready-state bootstrap")
        login_travel_app(client)

    def repair_mall_session(client):
        ensure_mall_backend_running(client)
        _clear_android_packages(client, ("gma.webapp.mall",), reason="loaded-snapshot repair")
        login_mall_app(client)

    def repair_meituan_session(client):
        ensure_meituan_backend_running(client)
        _clear_android_packages(client, ("gma.webapp.meituan",), reason="loaded-snapshot repair")
        login_meituan_app(client)

    def repair_xiaoshiliu_session(client):
        ensure_xiaoshiliu_backend_running(client)
        _clear_android_packages(client, ("gma.webapp.xiaoshiliu",), reason="loaded-snapshot repair")
        login_xiaoshiliu_app(client)

    def repair_hmdp_session(client):
        ensure_hmdp_backend_running(client)
        _clear_android_packages(client, ("gma.webapp.hmdp",), reason="loaded-snapshot repair")
        login_hmdp_app(client)

    def repair_travel_session(client):
        ensure_travel_backend_running(client)
        _clear_android_packages(client, ("gma.webapp.travel",), reason="loaded-snapshot repair")
        login_travel_app(client)

    requested_apps = set(apps or [])

    try:
        _configure_chrome_for_webapps(client)
    except Exception as e:
        logger.warning(f"Failed to configure Chrome for web apps: {e}")

    try:
        _ensure_ready_state_launcher_icons(client)
    except Exception as e:
        logger.warning(f"Failed to install ready-state web app wrappers before app repair: {e}")

    if not bootstrap_apps:
        # A loaded emulator snapshot restores Android disk state, but the apps
        # still depend on live backend/session repair after container restart.
        # Run the same app-level repairs without falling back to gma_init_state.
        for label, aliases, repair_fn, attempts in (
            ("Mattermost", (), repair_mattermost_app_state, 2),
            ("ElementX", (), reset_and_ensure_elementx, 3),
            ("Tempus", (), repair_tempus_app_state, 2),
            ("Mastodon", (), sync_mastodon_app_state, 2),
            ("Mall", (), repair_mall_session, 2),
            ("Meituan", (), repair_meituan_session, 2),
            ("XiaoShiLiu", ("Xiaoshiliu", "xiaoshiliu"), repair_xiaoshiliu_session, 2),
            ("HMDP", (), repair_hmdp_session, 2),
            ("Travel", (), repair_travel_session, 1),
        ):
            if requested_apps and label not in requested_apps and not (set(aliases) & requested_apps):
                continue
            for attempt in range(1, attempts + 1):
                try:
                    repair_fn(client)
                    break
                except Exception as e:
                    if attempt < attempts:
                        logger.warning(f"{label} loaded-snapshot repair failed, retrying")
                        time.sleep(2)
                        continue
                    logger.error(f"{label} loaded-snapshot repair failed: {e}")
                    return False
        try:
            _ensure_ready_state_launcher_icons(client)
        except Exception as e:
            logger.warning(f"Failed to repair ready-state launcher icons: {e}")
        _set_fixed_emulator_time(client)
        try:
            client.press_home()
        except Exception as e:
            logger.warning(f"Failed to return to home after ready-state repair: {e}")
        return True

    for label, aliases, ensure_fn, attempts in (
        ("Mattermost", (), sync_mattermost_app_state, 2),
        ("ElementX", (), reset_and_ensure_elementx, 2),
        ("Tempus", (), reset_and_ensure_tempus, 2),
        ("Mall", (), reset_and_ensure_mall, 1),
        ("Meituan", (), reset_and_ensure_meituan, 1),
        ("XiaoShiLiu", ("Xiaoshiliu", "xiaoshiliu"), reset_and_ensure_xiaoshiliu, 2),
        ("HMDP", (), reset_and_ensure_hmdp, 1),
        ("Travel", (), reset_and_ensure_travel, 1),
    ):
        if requested_apps and label not in requested_apps and not (set(aliases) & requested_apps):
            continue
        for attempt in range(1, attempts + 1):
            try:
                ensure_fn(client)
                break
            except Exception as e:
                if attempt < attempts:
                    logger.warning(f"{label} ready-state bootstrap failed, retrying")
                    time.sleep(2)
                    continue
                logger.error(f"{label} ready-state bootstrap failed: {e}")
                return False

    try:
        _ensure_ready_state_launcher_icons(client)
    except Exception as e:
        logger.warning(f"Failed to repair ready-state launcher icons: {e}")

    _set_fixed_emulator_time(client)
    try:
        client.press_home()
    except Exception as e:
        logger.warning(f"Failed to return to home after ready-state repair: {e}")
    return True


def prepare_task_environment(
    client,
    snapshot: str = "gma_ready_state",
    apps: set[str] | None = None,
) -> bool:
    """Load a snapshot, clear drift, then restore ready-state backends if needed."""
    logger.info("Preparing task environment")
    status = load_snapshot_state_status(client, snapshot=snapshot)
    if not status["ok"]:
        return False
    if not clear_environment(client, apps=apps):
        return False
    bootstrap_apps = not (
        snapshot == "gma_ready_state"
        and (status.get("loaded_snapshot") or status.get("used_live_state"))
    )
    return ensure_ready_state_apps(
        client,
        snapshot=snapshot,
        apps=apps,
        bootstrap_apps=bootstrap_apps,
    )


def reset_environment(client, snapshot: str = "gma_ready_state") -> bool:
    """Backward-compatible wrapper for task environment preparation."""
    return prepare_task_environment(client, snapshot=snapshot)
