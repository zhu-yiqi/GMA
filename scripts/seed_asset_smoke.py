from __future__ import annotations

import argparse
from pathlib import Path

from gma.assets import (
    AlarmAsset,
    CalendarEventAsset,
    ContactAsset,
    DeviceFileAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
    MastodonAccountAsset,
    MastodonFollowAsset,
    MastodonStatusAsset,
    MattermostChannelAsset,
    MattermostPostAsset,
    MattermostTeamAsset,
    MattermostUserAsset,
    SmsMessageAsset,
)
from gma.runtime.client import GMAClient


REPO_ROOT = Path(__file__).resolve().parents[1]
FILES_SMOKE_TEXT = REPO_ROOT / "docker/Pixel_8_API_34_x86_64.avd/read-snapshot.txt"
GALLERY_SMOKE_IMAGE = REPO_ROOT / "docker/Pixel_8_API_34_x86_64.avd/snapshots/gma_init_state/screenshot.png"


def build_assets() -> list:
    return [
        ContactAsset(
            name="Tom Asset",
            phone_number="+15550000001",
            email="tom.asset@example.com",
        ),
        SmsMessageAsset(
            address="15550000001",
            body="hello from sms asset",
            box="inbox",
        ),
        AlarmAsset(
            hour=6,
            minute=45,
            label="AssetAlarm",
        ),
        CalendarEventAsset(
            title="Asset Calendar Event",
            start_ms=1776583200000,
            end_ms=1776586800000,
            description="calendar seeded from asset",
            location="Room 101",
            timezone="UTC",
        ),
        DeviceFileAsset(
            app="Files",
            storage_dir="Download",
            filename="read-snapshot.txt",
            source_path=str(FILES_SMOKE_TEXT),
        ),
        DeviceFileAsset(
            app="Gallery",
            storage_dir="Pictures",
            filename="gallery-smoke.png",
            source_path=str(GALLERY_SMOKE_IMAGE),
        ),
        MailAccountAsset(
            display_name="Asset Inbox",
            email="asset@example.com",
        ),
        MailMessageAsset(
            mailbox="inbox",
            from_name="Alice Sender",
            from_email="alice@example.com",
            to=["asset@example.com"],
            subject="Asset Mail Subject",
            body="Mail body from asset system",
            attachments=[
                MailAttachment(
                    filename="mail-attachment.txt",
                    text_content="hello from attachment",
                    mime_type="text/plain",
                )
            ],
            read=False,
        ),
        MattermostTeamAsset(
            name="assetteam",
            display_name="Asset Team",
        ),
        MattermostChannelAsset(
            team="assetteam",
            name="general",
            display_name="General",
        ),
        MattermostUserAsset(
            username="tom.asset",
            email="tom.asset@example.com",
            first_name="Tom",
            last_name="Asset",
            team="assetteam",
            channel_memberships=["general"],
        ),
        MattermostPostAsset(
            team="assetteam",
            channel="general",
            username="tom.asset",
            message="hello from mattermost asset",
        ),
        MastodonAccountAsset(
            username="assetbot",
            email="assetbot@example.com",
            display_name="Asset Bot",
            bio="seeded by asset",
        ),
        MastodonStatusAsset(
            username="assetbot",
            text="hello from mastodon asset",
            visibility="public",
        ),
        MastodonFollowAsset(
            follower_username="assetbot",
            followed_username="owner",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed one smoke-test item per GMA asset category")
    parser.add_argument("--url", default="http://localhost:8100", help="GMA backend URL")
    parser.add_argument("--device", default="emulator-5554", help="ADB device id")
    args = parser.parse_args()

    client = GMAClient(args.url, device=args.device)
    client.init()
    assets = build_assets()
    client.apply_assets(assets)
    print(f"seeded {len(assets)} assets into {args.url} for {args.device}")


if __name__ == "__main__":
    main()
