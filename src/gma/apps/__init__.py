"""App registry — maps app names to package names and provides cleanup hooks.

Each app can register a cleanup function that the framework calls before
task setup to ensure a clean environment.
"""

from __future__ import annotations

from typing import Callable

from loguru import logger


# App name -> Android package name
APP_PACKAGES: dict[str, str] = {
    "Calendar": "org.fossify.calendar",
    "Chrome": "com.android.chrome",
    "Contacts": "com.google.android.contacts",
    "Clock": "com.google.android.deskclock",
    "Files": "com.google.android.documentsui",
    "ElementX": "io.element.android.x",
    "Gallery": "gallery.photomanager.picturegalleryapp.imagegallery",
    "Mail": "com.gmailclone",
    "Maps": "com.google.android.apps.maps",
    "Mastodon": "org.joinmastodon.android.mastodon",
    "Mattermost": "com.mattermost.rnbeta",
    "Mall": "com.android.chrome",
    "MallAdmin": "com.android.chrome",
    "Meituan": "com.android.chrome",
    "HMDP": "gma.webapp.hmdp",
    "Travel": "gma.webapp.travel",
    "Messages": "com.google.android.apps.messaging",
    "Tempus": "com.eddyizm.tempus.debug",
    "XiaoShiLiu": "com.android.chrome",
    "Settings": "com.android.settings",
    "Camera": "com.android.camera2",
}

APP_URLS: dict[str, str] = {
    "Mall": "http://10.0.2.2:8040",
    "MallAdmin": "http://10.0.2.2:8042",
    "Meituan": "http://10.0.2.2:8050/meituan/",
    "XiaoShiLiu": "http://10.0.2.2:8030",
    "HMDP": "http://10.0.2.2:8070/hmdp/",
    "Travel": "http://10.0.2.2:8060/trip",
}

APP_ALIASES: dict[str, str] = {
    "calendar": "org.fossify.calendar",
    "com.google.android.calendar": "org.fossify.calendar",
    "clock": "com.google.android.deskclock",
    "com.google.android.deskclock": "com.google.android.deskclock",
    "contacts": "com.google.android.contacts",
    "files": "com.google.android.documentsui",
    "gallery": "gallery.photomanager.picturegalleryapp.imagegallery",
    "mail": "com.gmailclone",
    "com.android.email": "com.gmailclone",
    "mall": "com.android.chrome",
    "mall-admin": "com.android.chrome",
    "mall_admin": "com.android.chrome",
    "meituan": "com.android.chrome",
    "hmdp": "gma.webapp.hmdp",
    "travel": "gma.webapp.travel",
    "messages": "com.google.android.apps.messaging",
    "sms": "com.google.android.apps.messaging",
    "com.google.android.apps.messaging": "com.google.android.apps.messaging",
    "xiaoshiliu": "com.android.chrome",
    "xiao_shi_liu": "com.android.chrome",
    "element x": "io.element.android.x",
}

APP_URL_ALIASES: dict[str, str] = {
    "mall": APP_URLS["Mall"],
    "mall-admin": APP_URLS["MallAdmin"],
    "mall_admin": APP_URLS["MallAdmin"],
    "meituan": APP_URLS["Meituan"],
    "hmdp": APP_URLS["HMDP"],
    "travel": APP_URLS["Travel"],
    "xiaoshiliu": APP_URLS["XiaoShiLiu"],
    "xiao_shi_liu": APP_URLS["XiaoShiLiu"],
}

# Cleanup hooks: app_name -> callable(client)
_CLEANUP_HOOKS: dict[str, Callable] = {}


def register_cleanup(app_name: str, hook: Callable) -> None:
    """Register a cleanup function for an app."""
    _CLEANUP_HOOKS[app_name] = hook


def get_package(app_name: str) -> str | None:
    """Look up the Android package name for an app."""
    return APP_PACKAGES.get(app_name)


def resolve_package(app_name_or_package: str) -> str:
    """Resolve an app name, alias, or package-like string to the launch package."""
    if not app_name_or_package:
        return app_name_or_package
    if app_name_or_package in APP_PACKAGES:
        return APP_PACKAGES[app_name_or_package]
    if app_name_or_package in APP_PACKAGES.values():
        return app_name_or_package
    lower = app_name_or_package.lower()
    if lower in APP_ALIASES:
        return APP_ALIASES[lower]
    for app_name, package in APP_PACKAGES.items():
        if lower == app_name.lower():
            return package
    return app_name_or_package


def resolve_launch_url(app_name_or_package: str) -> str | None:
    """Return a URL for Chrome-hosted web apps, if this label maps to one."""
    if not app_name_or_package:
        return None
    if app_name_or_package in APP_URLS:
        return APP_URLS[app_name_or_package]
    lower = app_name_or_package.lower()
    if lower in APP_URL_ALIASES:
        return APP_URL_ALIASES[lower]
    for app_name, url in APP_URLS.items():
        if lower == app_name.lower():
            return url
    return None


def register_app(name: str, package: str) -> None:
    """Register a new app."""
    APP_PACKAGES[name] = package


def cleanup_app(app_name: str, client) -> None:
    """Run the cleanup hook for an app, if one is registered."""
    hook = _CLEANUP_HOOKS.get(app_name)
    if hook:
        try:
            hook(client)
        except Exception as e:
            logger.warning(f"Cleanup hook for {app_name} failed: {e}")


def cleanup_all(client) -> None:
    """Run all registered cleanup hooks."""
    for app_name, hook in _CLEANUP_HOOKS.items():
        try:
            hook(client)
        except Exception as e:
            logger.warning(f"Cleanup hook for {app_name} failed: {e}")
