from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass

from gma.assets import (
    ElementXAttachmentAsset,
    ElementXMessageAsset,
    ElementXPollAsset,
    ElementXPollResponse,
    ElementXRoomAsset,
    ElementXUserAsset,
    TempusPlaylistAsset,
    apply_assets,
)
from gma.runtime.client import GMAClient


@dataclass
class SmokeSummary:
    suffix: str
    space_name: str
    group_name: str
    dm_name: str
    user_a: str
    user_b: str
    message_text: str
    poll_question: str
    attachment_caption: str
    playlist_name: str
    playlist_tracks: list[str]


def build_assets(suffix: str) -> tuple[list, SmokeSummary]:
    user_a = f"assetx{suffix}a"
    user_b = f"assetx{suffix}b"
    space_name = f"ElementX Smoke Space {suffix}"
    group_name = f"ElementX Smoke Group {suffix}"
    dm_name = f"ElementX Smoke DM {suffix}"
    space_alias = f"elementx-smoke-space-{suffix}"
    group_alias = f"elementx-smoke-group-{suffix}"
    dm_alias = f"elementx-smoke-dm-{suffix}"
    message_text = f"hello from elementx smoke {suffix}"
    poll_question = f"Where should we meet {suffix}?"
    attachment_caption = f"ElementX smoke attachment {suffix}"
    playlist_name = f"Tempus Smoke Playlist {suffix}"
    playlist_tracks = ["晴天", "她的睫毛", "止戰之殤"]

    assets = [
        ElementXUserAsset(
            username=user_a,
            password="password",
            display_name=f"ElementX Smoke Alice {suffix}",
        ),
        ElementXUserAsset(
            username=user_b,
            password="password",
            display_name=f"ElementX Smoke Bob {suffix}",
        ),
        ElementXRoomAsset(
            name=space_name,
            room_type="space",
            creator_username="testuser",
            creator_password="testpass123",
            alias_localpart=space_alias,
        ),
        ElementXRoomAsset(
            name=group_name,
            room_type="group",
            creator_username="testuser",
            creator_password="testpass123",
            members=[user_a, user_b],
            alias_localpart=group_alias,
            topic=f"ElementX smoke topic {suffix}",
            parent_space=space_name,
        ),
        ElementXRoomAsset(
            name=dm_name,
            room_type="dm",
            creator_username="testuser",
            creator_password="testpass123",
            members=[user_a],
            alias_localpart=dm_alias,
        ),
        ElementXMessageAsset(
            room=group_name,
            sender_username=user_a,
            sender_password="password",
            text=message_text,
        ),
        ElementXPollAsset(
            room=group_name,
            sender_username=user_a,
            sender_password="password",
            question=poll_question,
            options=["Cafe", "Office"],
            responses=[
                ElementXPollResponse(
                    username=user_b,
                    password="password",
                    option="Cafe",
                )
            ],
        ),
        ElementXAttachmentAsset(
            room=group_name,
            sender_username=user_a,
            sender_password="password",
            filename=f"elementx-smoke-{suffix}.txt",
            text_content=f"ElementX attachment body {suffix}",
            mime_type="text/plain",
            caption=attachment_caption,
        ),
        TempusPlaylistAsset(
            name=playlist_name,
            owner_username="testuserfjx",
            comment=f"tempus smoke playlist {suffix}",
            public=False,
            track_titles=playlist_tracks,
        ),
    ]

    summary = SmokeSummary(
        suffix=suffix,
        space_name=space_name,
        group_name=group_name,
        dm_name=dm_name,
        user_a=user_a,
        user_b=user_b,
        message_text=message_text,
        poll_question=poll_question,
        attachment_caption=attachment_caption,
        playlist_name=playlist_name,
        playlist_tracks=playlist_tracks,
    )
    return assets, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ElementX and Tempus smoke assets")
    parser.add_argument("--url", default="http://localhost:8100", help="GMA backend URL")
    parser.add_argument("--device", default="emulator-5554", help="ADB device id")
    parser.add_argument(
        "--suffix",
        default=time.strftime("%m%d%H%M%S"),
        help="Unique suffix for seeded data (default: current timestamp)",
    )
    parser.add_argument("--json", action="store_true", help="Print the seeded summary as JSON")
    args = parser.parse_args()

    client = GMAClient(args.url, device=args.device)
    client.init()
    assets, summary = build_assets(args.suffix)
    apply_assets(client, assets)

    if args.json:
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        return

    print(f"seeded {len(assets)} assets into {args.url} for {args.device}")
    print(f"ElementX space: {summary.space_name}")
    print(f"ElementX group: {summary.group_name}")
    print(f"ElementX DM: {summary.dm_name}")
    print(f"ElementX users: {summary.user_a}, {summary.user_b}")
    print(f"ElementX message: {summary.message_text}")
    print(f"ElementX poll: {summary.poll_question}")
    print(f"ElementX attachment: {summary.attachment_caption}")
    print(f"Tempus playlist: {summary.playlist_name}")
    print("Tempus tracks: " + ", ".join(summary.playlist_tracks))


if __name__ == "__main__":
    main()
