from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


def _parse_readable_timestamp_ms(value: Any) -> Any:
    """Accept YYYYMMDDHHMM UTC timestamps while preserving epoch-ms values."""
    if value is None:
        return None
    raw = str(value).strip()
    if len(raw) == 12 and raw.isdigit() and raw.startswith("20"):
        dt = datetime.strptime(raw, "%Y%m%d%H%M").replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    return value


class TimestampedBaseModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def normalize_readable_timestamps(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for key, value in list(normalized.items()):
            if key.endswith("_ms"):
                normalized[key] = _parse_readable_timestamp_ms(value)
        return normalized


class AssetBase(TimestampedBaseModel):
    kind: str
    app: str


class ContactAsset(AssetBase):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["contact"] = "contact"
    app: Literal["Contacts"] = "Contacts"
    name: str | None = None
    phone_number: str
    phone_label: str | None = None
    email: str | None = None
    email_label: str | None = None
    website: str | None = None
    notes: str | None = None
    label: str | None = None

    @model_validator(mode="after")
    def validate_labels(self):
        for field_name in ("phone_label", "email_label", "label"):
            label = getattr(self, field_name)
            if label is not None and not label.strip():
                raise ValueError(f"{field_name} must be non-empty when set")
        if self.label is not None and "/" in self.label:
            raise ValueError("label must not contain '/'")
        return self


class SmsMessageAsset(AssetBase):
    kind: Literal["sms_message"] = "sms_message"
    app: Literal["Messages"] = "Messages"
    address: str
    body: str
    box: Literal["inbox", "sent"] = "inbox"
    timestamp_ms: int | None = None
    read: bool = True


ClockAlarmWeekday = Literal[
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
_CLOCK_WEEKDAY_ORDER = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class AlarmAsset(AssetBase):
    kind: Literal["alarm"] = "alarm"
    app: Literal["Clock"] = "Clock"
    hour: int
    minute: int
    label: str | None = None
    enabled: bool = True
    days_of_week: tuple[ClockAlarmWeekday, ...] = ()
    vibrate: bool | None = None
    scheduled_year: int | None = None
    scheduled_month: int | None = None
    scheduled_day: int | None = None

    @model_validator(mode="after")
    def normalize_days_of_week(self):
        seen: set[str] = set()
        normalized: list[ClockAlarmWeekday] = []
        for day in self.days_of_week:
            if day in seen:
                continue
            seen.add(day)
            normalized.append(day)
        normalized.sort(key=_CLOCK_WEEKDAY_ORDER.__getitem__)
        self.days_of_week = tuple(normalized)
        scheduled_parts = (self.scheduled_year, self.scheduled_month, self.scheduled_day)
        if any(value is not None for value in scheduled_parts):
            if not all(value is not None for value in scheduled_parts):
                raise ValueError(
                    "scheduled_year, scheduled_month, and scheduled_day must be set together"
                )
            if not 1 <= int(self.scheduled_month) <= 12:
                raise ValueError("scheduled_month must be in 1..12")
            if not 1 <= int(self.scheduled_day) <= 31:
                raise ValueError("scheduled_day must be in 1..31")
        return self


class CalendarEventAsset(AssetBase):
    kind: Literal["calendar_event"] = "calendar_event"
    app: Literal["Calendar"] = "Calendar"
    title: str
    start_ms: int
    end_ms: int
    description: str | None = None
    location: str | None = None
    timezone: str | None = None
    reminder_minutes: tuple[int, ...] = ()

    @model_validator(mode="after")
    def validate_reminders(self):
        if len(self.reminder_minutes) > 3:
            raise ValueError("CalendarEventAsset supports at most three reminders")
        if any(minutes < 0 for minutes in self.reminder_minutes):
            raise ValueError("reminder_minutes values must be non-negative")
        return self


class DeviceFileAsset(AssetBase):
    kind: Literal["device_file"] = "device_file"
    app: Literal["Files", "Gallery"]
    storage_dir: Literal[
        "Alarms",
        "DCIM/Camera",
        "Documents",
        "Download",
        "Movies",
        "Music",
        "Pictures",
    ]
    filename: str
    mime_type: str | None = None
    source_path: str | None = None
    text_content: str | None = None
    content_b64: str | None = None
    match_filename: bool = True

    @model_validator(mode="after")
    def validate_content_source(self):
        count = sum(
            value is not None
            for value in (self.source_path, self.text_content, self.content_b64)
        )
        if count != 1:
            raise ValueError(
                "Exactly one of source_path, text_content, or content_b64 must be set"
            )
        if self.app == "Gallery" and self.storage_dir not in {"Pictures", "DCIM/Camera"}:
            raise ValueError("Gallery assets must target Pictures or DCIM/Camera")
        if "/" in self.filename or not self.filename:
            raise ValueError("filename must be a simple basename")
        return self


class ImageContentExpectation(TimestampedBaseModel):
    filename: str | None = None
    source_path: str | None = None
    content_b64: str | None = None

    @model_validator(mode="after")
    def validate_content_source(self):
        count = sum(value is not None for value in (self.source_path, self.content_b64))
        if count != 1:
            raise ValueError("Exactly one of source_path or content_b64 must be set")
        if self.filename is not None and ("/" in self.filename or not self.filename):
            raise ValueError("filename must be a simple basename")
        return self


class MailAttachment(TimestampedBaseModel):
    filename: str
    mime_type: str | None = None
    source_path: str | None = None
    text_content: str | None = None
    content_b64: str | None = None

    @model_validator(mode="after")
    def validate_content_source(self):
        count = sum(
            value is not None
            for value in (self.source_path, self.text_content, self.content_b64)
        )
        if count != 1:
            raise ValueError(
                "Exactly one of source_path, text_content, or content_b64 must be set"
            )
        if "/" in self.filename or not self.filename:
            raise ValueError("filename must be a simple basename")
        if self.mime_type and self.mime_type.lower().startswith("image/"):
            raise ValueError("Mail image attachments are not supported")
        if Path(self.filename).suffix.lower() in {".apng", ".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}:
            raise ValueError("Mail image attachments are not supported")
        return self


class ElementXUserAsset(AssetBase):
    kind: Literal["elementx_user"] = "elementx_user"
    app: Literal["ElementX"] = "ElementX"
    username: str
    password: str = "password"
    display_name: str | None = None


class ElementXSessionAsset(AssetBase):
    kind: Literal["elementx_session"] = "elementx_session"
    app: Literal["ElementX"] = "ElementX"
    username: str
    password: str = "password"


class ElementXRoomAsset(AssetBase):
    kind: Literal["elementx_room"] = "elementx_room"
    app: Literal["ElementX"] = "ElementX"
    name: str
    room_type: Literal["dm", "group", "space"] | None = None
    creator_username: str = "testuser"
    creator_password: str = "testpass123"
    members: list[str] = Field(default_factory=list)
    member_passwords: dict[str, str] = Field(default_factory=dict)
    alias_localpart: str | None = None
    topic: str | None = None
    encrypted: bool = False
    parent_space: str | None = None
    created_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_room_shape(self):
        if self.room_type == "dm" and len(self.members) != 1:
            raise ValueError("ElementX DM rooms must include exactly one invited member")
        if self.room_type == "space" and self.parent_space is not None:
            raise ValueError("ElementX spaces cannot be nested under parent_space in v1")
        return self


class ElementXMessageAsset(AssetBase):
    kind: Literal["elementx_message"] = "elementx_message"
    app: Literal["ElementX"] = "ElementX"
    room: str
    sender_username: str
    sender_password: str = "password"
    text: str
    mentions_room: bool | None = None
    created_at_ms: int | None = None
    reply_to_text: str | None = None
    reply_to_sender_username: str | None = None
    pinned: bool | None = None
    pinning_username: str = "testuser"
    pinning_password: str = "testpass123"


class ElementXFileAsset(AssetBase):
    kind: Literal["elementx_file"] = "elementx_file"
    app: Literal["ElementX"] = "ElementX"
    room: str
    sender_username: str
    sender_password: str = "password"
    filename: str
    mime_type: str | None = None
    created_at_ms: int | None = None
    source_path: str | None = None
    text_content: str | None = None
    content_b64: str | None = None
    pinned: bool | None = None
    pinning_username: str = "testuser"
    pinning_password: str = "testpass123"

    @model_validator(mode="after")
    def validate_content_source(self):
        count = sum(
            value is not None
            for value in (self.source_path, self.text_content, self.content_b64)
        )
        if count != 1:
            raise ValueError(
                "Exactly one of source_path, text_content, or content_b64 must be set"
            )
        if "/" in self.filename or not self.filename:
            raise ValueError("filename must be a simple basename")
        return self


class ElementXPollResponse(TimestampedBaseModel):
    username: str
    option: str
    password: str = "password"
    created_at_ms: int | None = None


class ElementXPollAsset(AssetBase):
    kind: Literal["elementx_poll"] = "elementx_poll"
    app: Literal["ElementX"] = "ElementX"
    room: str
    sender_username: str
    sender_password: str = "password"
    question: str
    options: list[str]
    responses: list[ElementXPollResponse] = []
    created_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_poll(self):
        if len(self.options) < 2:
            raise ValueError("ElementX polls require at least two options")
        option_set = set(self.options)
        for response in self.responses:
            if response.option not in option_set:
                raise ValueError(f"Poll response option not found in options: {response.option}")
        return self


class MailReplyReference(TimestampedBaseModel):
    from_email: str
    subject: str


class MailAccountAsset(AssetBase):
    kind: Literal["mail_account"] = "mail_account"
    app: Literal["Mail"] = "Mail"
    display_name: str
    email: str


class MailMessageAsset(AssetBase):
    kind: Literal["mail_message"] = "mail_message"
    app: Literal["Mail"] = "Mail"
    mailbox: Literal["inbox", "sent", "drafts"] = "inbox"
    from_name: str | None = None
    from_email: str
    to: list[str]
    subject: str
    body: str
    attachments: list[MailAttachment] = []
    timestamp_ms: int | None = None
    read: bool = True
    reply_to: MailReplyReference | None = None


class MattermostTeamAsset(AssetBase):
    kind: Literal["mattermost_team"] = "mattermost_team"
    app: Literal["Mattermost"] = "Mattermost"
    name: str
    display_name: str
    team_type: Literal["O", "I"] = "O"
    description: str | None = None
    allow_open_invite: bool = True


class MattermostChannelAsset(AssetBase):
    kind: Literal["mattermost_channel"] = "mattermost_channel"
    app: Literal["Mattermost"] = "Mattermost"
    team: str
    name: str
    display_name: str | None = None
    channel_type: Literal["O", "P"] | None = None
    header: str | None = None
    purpose: str | None = None


class MattermostUserAsset(AssetBase):
    kind: Literal["mattermost_user"] = "mattermost_user"
    app: Literal["Mattermost"] = "Mattermost"
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    team: str | None = None
    channel_memberships: list[str] = Field(default_factory=list)


class MattermostChannelMembershipAsset(AssetBase):
    kind: Literal["mattermost_channel_membership"] = "mattermost_channel_membership"
    app: Literal["Mattermost"] = "Mattermost"
    team: str
    channel: str
    username: str


class MattermostPostAsset(AssetBase):
    kind: Literal["mattermost_post"] = "mattermost_post"
    app: Literal["Mattermost"] = "Mattermost"
    team: str
    channel: str
    username: str
    message: str
    root_message: str | None = None
    root_username: str | None = None
    create_at_ms: int | None = None
    props: dict = Field(default_factory=dict)
    pinned: bool | None = None
    pinning_username: str | None = "admin"
    pinning_password: str = "password"


class MattermostFilePostAsset(AssetBase):
    kind: Literal["mattermost_file_post"] = "mattermost_file_post"
    app: Literal["Mattermost"] = "Mattermost"
    team: str
    channel: str
    username: str
    message: str
    filename: str
    mime_type: str | None = None
    root_message: str | None = None
    root_username: str | None = None
    create_at_ms: int | None = None
    props: dict = Field(default_factory=dict)
    source_path: str | None = None
    text_content: str | None = None
    content_b64: str | None = None
    pinned: bool | None = None
    pinning_username: str | None = "admin"
    pinning_password: str = "password"

    @model_validator(mode="after")
    def validate_content_source(self):
        count = sum(
            value is not None
            for value in (self.source_path, self.text_content, self.content_b64)
        )
        if count != 1:
            raise ValueError(
                "Exactly one of source_path, text_content, or content_b64 must be set"
            )
        if "/" in self.filename or not self.filename:
            raise ValueError("filename must be a simple basename")
        return self


class MattermostSessionAsset(AssetBase):
    kind: Literal["mattermost_session"] = "mattermost_session"
    app: Literal["Mattermost"] = "Mattermost"
    username: str
    password: str = "password"


class MattermostDirectChannelAsset(AssetBase):
    kind: Literal["mattermost_direct_channel"] = "mattermost_direct_channel"
    app: Literal["Mattermost"] = "Mattermost"
    usernames: tuple[str, str]

    @model_validator(mode="after")
    def validate_usernames(self):
        if len(self.usernames) != 2 or self.usernames[0] == self.usernames[1]:
            raise ValueError("Mattermost direct channels require two distinct usernames")
        return self


class MattermostDirectPostAsset(AssetBase):
    kind: Literal["mattermost_direct_post"] = "mattermost_direct_post"
    app: Literal["Mattermost"] = "Mattermost"
    username: str
    other_username: str
    message: str
    root_message: str | None = None
    root_username: str | None = None
    create_at_ms: int | None = None
    props: dict = Field(default_factory=dict)


class MattermostReactionAsset(AssetBase):
    kind: Literal["mattermost_reaction"] = "mattermost_reaction"
    app: Literal["Mattermost"] = "Mattermost"
    team: str
    channel: str
    post_message: str
    username: str
    emoji_name: str
    post_username: str | None = None


class TempusPlaylistAsset(AssetBase):
    kind: Literal["tempus_playlist"] = "tempus_playlist"
    app: Literal["Tempus"] = "Tempus"
    name: str
    owner_username: str = "testuserfjx"
    comment: str | None = None
    visibility: Literal["public", "private"] | None = None
    public: bool | None = Field(
        default=None,
        description="Deprecated alias for visibility. Prefer visibility='public' or 'private'.",
    )
    track_titles: list[str]
    track_albums: dict[str, str] = Field(
        default_factory=dict,
        description="Optional title-to-album constraints for disambiguating songs with duplicate titles.",
    )
    track_match: Literal["exact", "contains"] = "exact"

    @model_validator(mode="after")
    def validate_tracks(self):
        if not self.track_titles:
            raise ValueError("Tempus playlists require at least one track title")
        unknown_albums = set(self.track_albums) - set(self.track_titles)
        if unknown_albums:
            raise ValueError(
                "Tempus playlist track_albums keys must also appear in track_titles: "
                + ", ".join(sorted(unknown_albums))
            )
        if self.visibility is not None and self.public is not None:
            expected_public = self.visibility == "public"
            if self.public != expected_public:
                raise ValueError("Tempus playlist visibility and public fields conflict")
        if self.visibility is None and self.public is not None:
            self.visibility = "public" if self.public else "private"
        elif self.visibility is not None and self.public is None:
            self.public = self.visibility == "public"
        return self


class TempusFavoriteAsset(AssetBase):
    kind: Literal["tempus_favorite"] = "tempus_favorite"
    app: Literal["Tempus"] = "Tempus"
    item_type: Literal["song", "album"] = "song"
    track_title: str | None = None
    album_name: str | None = None
    owner_username: str = "testuserfjx"

    @model_validator(mode="after")
    def validate_target(self):
        if self.item_type == "song" and not self.track_title:
            raise ValueError("Tempus song favorites require track_title")
        if self.item_type == "album" and not self.album_name:
            raise ValueError("Tempus album favorites require album_name")
        return self


class TempusUserAsset(AssetBase):
    kind: Literal["tempus_user"] = "tempus_user"
    app: Literal["Tempus"] = "Tempus"
    username: str
    password: str = "testpass123"
    name: str | None = None
    email: str | None = None
    is_admin: bool = False


class TempusSessionAsset(AssetBase):
    kind: Literal["tempus_session"] = "tempus_session"
    app: Literal["Tempus"] = "Tempus"
    username: str = "testuserfjx"
    password: str = "testpass123"


class MastodonAccountAsset(AssetBase):
    kind: Literal["mastodon_account"] = "mastodon_account"
    app: Literal["Mastodon"] = "Mastodon"
    username: str
    email: str
    display_name: str | None = None
    bio: str | None = None
    password: str | None = None


class MastodonSessionAsset(AssetBase):
    kind: Literal["mastodon_session"] = "mastodon_session"
    app: Literal["Mastodon"] = "Mastodon"
    username: str


class MastodonMediaAttachment(TimestampedBaseModel):
    filename: str | None = None
    mime_type: str | None = None
    description: str | None = None
    match_filename: bool = False
    source_path: str | None = None
    text_content: str | None = None
    content_b64: str | None = None

    @model_validator(mode="after")
    def validate_filename(self):
        if self.filename is not None and ("/" in self.filename or not self.filename):
            raise ValueError("filename must be a simple basename")
        return self


class MastodonPollSpec(TimestampedBaseModel):
    options: tuple[str, ...]
    multiple: bool = False
    hide_totals: bool = False
    expires_in_seconds: int = 86_400
    expires_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_poll(self):
        if len(self.options) < 2:
            raise ValueError("Mastodon polls require at least two options")
        if any(not option.strip() for option in self.options):
            raise ValueError("Mastodon poll options cannot be blank")
        if len(set(self.options)) != len(self.options):
            raise ValueError("Mastodon poll options must be unique")
        if self.expires_in_seconds <= 0:
            raise ValueError("expires_in_seconds must be positive")
        return self


class MastodonStatusAsset(AssetBase):
    kind: Literal["mastodon_status"] = "mastodon_status"
    app: Literal["Mastodon"] = "Mastodon"
    username: str
    text: str
    visibility: Literal["public", "unlisted", "private", "direct"] = "public"
    created_at_ms: int | None = None
    reply_to_id: str | None = None
    reply_to_username: str | None = None
    reply_to_text: str | None = None
    spoiler_text: str | None = None
    sensitive: bool = False
    media_attachments: tuple[MastodonMediaAttachment, ...] = ()
    poll: MastodonPollSpec | None = None

    @model_validator(mode="after")
    def validate_status_shape(self):
        if (self.reply_to_username is None) != (self.reply_to_text is None):
            raise ValueError("reply_to_username and reply_to_text must be set together")
        if self.reply_to_id is not None and self.reply_to_username is not None:
            raise ValueError("Use either reply_to_id or reply_to_username/reply_to_text, not both")
        if self.poll is not None and self.media_attachments:
            raise ValueError("Mastodon statuses cannot include both poll and media attachments")
        return self


class MastodonMediaStatusAsset(MastodonStatusAsset):
    kind: Literal["mastodon_media_status"] = "mastodon_media_status"
    media_attachments: tuple[MastodonMediaAttachment, ...]

    @model_validator(mode="after")
    def validate_media_status(self):
        super().validate_status_shape()
        if not self.media_attachments:
            raise ValueError("Mastodon media statuses require at least one media attachment")
        return self


class MastodonPollStatusAsset(MastodonStatusAsset):
    kind: Literal["mastodon_poll_status"] = "mastodon_poll_status"
    poll: MastodonPollSpec


class MastodonFollowAsset(AssetBase):
    kind: Literal["mastodon_follow"] = "mastodon_follow"
    app: Literal["Mastodon"] = "Mastodon"
    follower_username: str
    followed_username: str


class MastodonStatusInteractionAsset(AssetBase):
    app: Literal["Mastodon"] = "Mastodon"
    actor_username: str
    target_username: str
    target_text: str


class MastodonFavoriteAsset(MastodonStatusInteractionAsset):
    kind: Literal["mastodon_favorite"] = "mastodon_favorite"


class MastodonReblogAsset(MastodonStatusInteractionAsset):
    kind: Literal["mastodon_reblog"] = "mastodon_reblog"


class MastodonBookmarkAsset(MastodonStatusInteractionAsset):
    kind: Literal["mastodon_bookmark"] = "mastodon_bookmark"


class MastodonPollVoteAsset(AssetBase):
    kind: Literal["mastodon_poll_vote"] = "mastodon_poll_vote"
    app: Literal["Mastodon"] = "Mastodon"
    voter_username: str
    poll_username: str
    poll_text: str
    choices: tuple[str, ...]

    @model_validator(mode="after")
    def validate_choices(self):
        if not self.choices:
            raise ValueError("Mastodon poll votes require at least one choice")
        return self


class XiaoShiLiuUserAsset(AssetBase):
    kind: Literal["xiaoshiliu_user"] = "xiaoshiliu_user"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    user_id: str
    password: str = "123456"
    nickname: str | None = None
    email: str | None = None
    avatar: str | None = "/assets/avatar-ClIy5dZi.png"
    bio: str | None = None
    location: str | None = None
    gender: str | None = None
    zodiac_sign: str | None = None
    mbti: str | None = None
    education: str | None = None
    major: str | None = None
    interests: list[str] = Field(default_factory=list)
    verified: bool = False
    is_active: bool = True


class XiaoShiLiuSessionAsset(AssetBase):
    kind: Literal["xiaoshiliu_session"] = "xiaoshiliu_session"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    user_id: str
    password: str = "123456"


class XiaoShiLiuPostAsset(AssetBase):
    kind: Literal["xiaoshiliu_post"] = "xiaoshiliu_post"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    author_user_id: str
    title: str
    content: str
    category: str | None = None
    post_type: Literal["image", "video"] = "image"
    status: Literal["published", "draft", "pending"] = "published"
    tags: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    min_image_count: int = Field(default=0, ge=0)
    expected_images: tuple[ImageContentExpectation, ...] = ()
    video_url: str | None = None
    cover_url: str | None = None
    created_at_ms: int | None = None
    share_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_post_media(self):
        if self.post_type == "video" and not self.video_url:
            raise ValueError("XiaoShiLiu video posts require video_url")
        return self


class XiaoShiLiuCommentAsset(AssetBase):
    kind: Literal["xiaoshiliu_comment"] = "xiaoshiliu_comment"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    post_title: str
    post_author_user_id: str
    author_user_id: str
    content: str
    created_at_ms: int | None = None
    parent_content: str | None = None
    parent_author_user_id: str | None = None

    @model_validator(mode="after")
    def validate_parent(self):
        if bool(self.parent_content) != bool(self.parent_author_user_id):
            raise ValueError("parent_content and parent_author_user_id must be set together")
        return self


class XiaoShiLiuLikeAsset(AssetBase):
    kind: Literal["xiaoshiliu_like"] = "xiaoshiliu_like"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    user_id: str
    target_type: Literal["post", "comment"] = "post"
    post_title: str
    post_author_user_id: str
    comment_content: str | None = None
    comment_author_user_id: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.target_type == "comment" and not (self.comment_content and self.comment_author_user_id):
            raise ValueError("Comment likes require comment_content and comment_author_user_id")
        return self


class XiaoShiLiuCollectionAsset(AssetBase):
    kind: Literal["xiaoshiliu_collection"] = "xiaoshiliu_collection"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    user_id: str
    post_title: str
    post_author_user_id: str


class XiaoShiLiuFollowAsset(AssetBase):
    kind: Literal["xiaoshiliu_follow"] = "xiaoshiliu_follow"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    follower_user_id: str
    following_user_id: str

    @model_validator(mode="after")
    def validate_users(self):
        if self.follower_user_id == self.following_user_id:
            raise ValueError("A XiaoShiLiu user cannot follow itself")
        return self


class XiaoShiLiuNotificationAsset(AssetBase):
    kind: Literal["xiaoshiliu_notification"] = "xiaoshiliu_notification"
    app: Literal["XiaoShiLiu"] = "XiaoShiLiu"
    user_id: str
    sender_user_id: str
    notification_type: Literal[
        "like_post",
        "like_comment",
        "collection",
        "comment",
        "reply",
        "follow",
        "mention_comment",
        "mention",
    ]
    title: str | None = None
    post_title: str | None = None
    post_author_user_id: str | None = None
    comment_content: str | None = None
    comment_author_user_id: str | None = None
    is_read: bool = False
    created_at_ms: int | None = None


class MallMemberAsset(AssetBase):
    kind: Literal["mall_member"] = "mall_member"
    app: Literal["Mall"] = "Mall"
    username: str
    password: str = "123456"
    nickname: str | None = None
    phone: str | None = None
    icon: str | None = "http://10.0.2.2:8040/static/temp/banner1.jpg"
    gender: int | None = None
    birthday: str | None = None
    city: str | None = None
    job: str | None = None
    personalized_signature: str | None = None
    status: int = 1


class MallSessionAsset(AssetBase):
    kind: Literal["mall_session"] = "mall_session"
    app: Literal["Mall"] = "Mall"
    username: str
    password: str = "123456"


class MallAddressAsset(AssetBase):
    kind: Literal["mall_address"] = "mall_address"
    app: Literal["Mall"] = "Mall"
    member_username: str
    name: str
    phone_number: str
    province: str | None = None
    city: str | None = None
    region: str | None = None
    detail_address: str
    post_code: str | None = None
    default_status: bool = False


class MallProductAsset(AssetBase):
    kind: Literal["mall_product"] = "mall_product"
    app: Literal["Mall"] = "Mall"
    name: str
    product_sn: str
    price: float
    stock: int = 100
    sub_title: str | None = None
    description: str | None = None
    pic: str | None = "http://10.0.2.2:8040/static/temp/banner1.jpg"
    brand_name: str | None = None
    product_category_name: str | None = None
    publish_status: bool = True
    delete_status: bool = False
    sku_code: str | None = None


class MallBrandAsset(AssetBase):
    kind: Literal["mall_brand"] = "mall_brand"
    app: Literal["Mall"] = "Mall"
    name: str
    first_letter: str | None = None
    sort: int = 0
    factory_status: bool = True
    show_status: bool = True
    logo: str | None = "http://10.0.2.2:8040/static/temp/banner1.jpg"
    big_pic: str | None = "http://10.0.2.2:8040/static/temp/banner1.jpg"
    brand_story: str | None = None
    products: list[MallProductAsset] = Field(default_factory=list)


class MallCartItemAsset(AssetBase):
    kind: Literal["mall_cart_item"] = "mall_cart_item"
    app: Literal["Mall"] = "Mall"
    member_username: str
    product_sn: str
    quantity: int = 1
    delete_status: bool = False


class MallOrderItem(TimestampedBaseModel):
    product_sn: str
    quantity: int = 1
    price: float | None = None


class MallOrderAsset(AssetBase):
    kind: Literal["mall_order"] = "mall_order"
    app: Literal["Mall"] = "Mall"
    order_sn: str
    member_username: str
    items: list[MallOrderItem]
    status: int = 0
    receiver_name: str
    receiver_phone: str
    receiver_province: str | None = None
    receiver_city: str | None = None
    receiver_region: str | None = None
    receiver_detail_address: str
    note: str | None = None
    created_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_items(self):
        if not self.items:
            raise ValueError("Mall orders require at least one item")
        return self


class MallReviewAsset(AssetBase):
    kind: Literal["mall_review"] = "mall_review"
    app: Literal["Mall"] = "Mall"
    order_sn: str
    product_sn: str
    member_username: str
    content: str
    star: int = 5
    show_status: int = 1
    created_at_ms: int | None = None


class MeituanUserAsset(AssetBase):
    kind: Literal["meituan_user"] = "meituan_user"
    app: Literal["Meituan"] = "Meituan"
    username: str
    password: str = "123456"
    user_id: int | None = None
    status: int = 1
    city: str | None = None
    avatar: str | None = "/img/delivery-avatar.61d561c7.png"


class MeituanSessionAsset(AssetBase):
    kind: Literal["meituan_session"] = "meituan_session"
    app: Literal["Meituan"] = "Meituan"
    username: str
    password: str = "123456"


class MeituanRestaurantAsset(AssetBase):
    kind: Literal["meituan_restaurant"] = "meituan_restaurant"
    app: Literal["Meituan"] = "Meituan"
    name: str
    restaurant_id: int | None = None
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    pic_url: str = "/img/restaurant.a244c07f.jpg"
    min_price: float = 0
    shipping_fee: float = 0
    month_sales: int = 0
    wm_poi_score: float = 5
    bulletin: str | None = None


class MeituanFoodAsset(AssetBase):
    kind: Literal["meituan_food"] = "meituan_food"
    app: Literal["Meituan"] = "Meituan"
    restaurant_name: str
    name: str
    price: float
    category_name: str = "Asset Check"
    food_id: int | None = None
    sku_id: int | None = None
    pic_url: str = "/img/restaurant.a244c07f.jpg"
    description: str | None = None
    month_saled: int = 0


class MeituanAddressAsset(AssetBase):
    kind: Literal["meituan_address"] = "meituan_address"
    app: Literal["Meituan"] = "Meituan"
    user_id: int
    name: str
    phone: str
    address: str
    address_detail: str
    label: str = "Office"
    gender: Literal["male", "female"] = "male"
    province: str | None = None
    city: str | None = None


class MeituanCartItemAsset(AssetBase):
    kind: Literal["meituan_cart_item"] = "meituan_cart_item"
    app: Literal["Meituan"] = "Meituan"
    user_id: int
    restaurant_name: str
    food_name: str
    quantity: int = 1
    spec: str = ""


class MeituanOrderFood(TimestampedBaseModel):
    food_name: str
    quantity: int = 1
    price: float | None = None
    spec: str = ""


class MeituanOrderAsset(AssetBase):
    kind: Literal["meituan_order"] = "meituan_order"
    app: Literal["Meituan"] = "Meituan"
    user_id: int
    restaurant_name: str
    foods: list[MeituanOrderFood]
    status: str = "Unpaid"
    address_name: str
    order_id: int | None = None
    remark: str = ""
    code: int | None = None
    delivery_status: int | None = None
    has_comment: bool | None = None
    created_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_foods(self):
        if not self.foods:
            raise ValueError("Meituan orders require at least one food")
        return self


class MeituanCollectionAsset(AssetBase):
    kind: Literal["meituan_collection"] = "meituan_collection"
    app: Literal["Meituan"] = "Meituan"
    user_id: int
    restaurant_name: str


class MeituanCommentAsset(AssetBase):
    kind: Literal["meituan_comment"] = "meituan_comment"
    app: Literal["Meituan"] = "Meituan"
    user_id: int
    user_name: str
    restaurant_name: str
    content: str
    food_score: int = 5
    delivery_score: int = 5
    order_id: int | None = None
    created_at_ms: int | None = None


class TravelUserAsset(AssetBase):
    kind: Literal["travel_user"] = "travel_user"
    app: Literal["Travel"] = "Travel"
    email: str
    username: str | None = None
    password: str = "123456"
    first_name: str = "Asset"
    last_name: str = "Traveler"
    phone: str | None = None


class TravelFlightBookingAsset(AssetBase):
    kind: Literal["travel_flight_booking"] = "travel_flight_booking"
    app: Literal["Travel"] = "Travel"
    user_email: str
    from_airport: str
    to_airport: str
    departure_date_ms: int
    flight_code: str | None = None
    passenger_first_name: str | None = None
    passenger_last_name: str | None = None
    passenger_email: str | None = None
    passenger_phone: str | None = None
    passenger_phone_dial_code: str | None = None
    passenger_type: Literal["adult", "child", "infant"] = "adult"
    passenger_count: int | None = None
    passenger_gender: Literal["male", "female", "other"] = "other"
    passenger_country: str = "United States"
    passenger_birth_ms: int | None = None
    passport_number: str | None = None
    passport_expiry_ms: int | None = None
    frequent_flyer_airline: str | None = None
    frequent_flyer_number: str | None = None
    seat_class: str = "economy"
    payment_status: str = "paid"
    ticket_status: str = "confirmed"
    currency: str = "USD"
    total_fare: float | None = None
    pnr_code: str | None = None
    user_timezone: str = "Asia/Shanghai"
    booked_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_passenger_count(self):
        if self.passenger_count is not None and self.passenger_count <= 0:
            raise ValueError("Travel flight booking passenger_count must be positive")
        return self


class TravelHotelGuest(TimestampedBaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    guest_type: Literal["adult", "child"] = "adult"
    age: int | None = None


class TravelHotelRoomSelection(TimestampedBaseModel):
    room_type: str | None = None
    room_number: str | None = None
    bed_options: str | None = None
    count: int = 1

    @model_validator(mode="after")
    def validate_room_identity(self):
        if not (self.room_type or self.room_number or self.bed_options):
            raise ValueError("Travel hotel room selection requires room_type, room_number, or bed_options")
        if self.count <= 0:
            raise ValueError("Travel hotel room selection count must be positive")
        return self


class TravelHotelBookingAsset(AssetBase):
    kind: Literal["travel_hotel_booking"] = "travel_hotel_booking"
    app: Literal["Travel"] = "Travel"
    user_email: str
    hotel_name: str | None = None
    hotel_slug: str | None = None
    check_in_ms: int
    check_out_ms: int
    guest_first_name: str | None = None
    guest_last_name: str | None = None
    guest_phone: str | None = None
    guest_type: Literal["adult", "child"] = "adult"
    guest_count: int | None = None
    room_count: int | None = None
    guest_age: int | None = None
    booking_status: str = "confirmed"
    payment_status: str = "paid"
    payment_method: str = "card"
    total_price: float | None = None
    booked_at_ms: int | None = None
    guests: list[TravelHotelGuest] = Field(default_factory=list)
    room_selections: list[TravelHotelRoomSelection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_hotel_identity(self):
        if not (self.hotel_name or self.hotel_slug):
            raise ValueError("Travel hotel booking requires hotel_name or hotel_slug")
        if self.check_out_ms <= self.check_in_ms:
            raise ValueError("Travel hotel booking check_out_ms must be after check_in_ms")
        if self.guest_count is not None and self.guest_count <= 0:
            raise ValueError("Travel hotel booking guest_count must be positive")
        if self.room_count is not None and self.room_count <= 0:
            raise ValueError("Travel hotel booking room_count must be positive")
        if self.guests and self.guest_count is not None and len(self.guests) != self.guest_count:
            raise ValueError("Travel hotel booking guests length must match guest_count")
        if self.room_selections:
            total_rooms = sum(selection.count for selection in self.room_selections)
            if self.room_count is not None and total_rooms != self.room_count:
                raise ValueError("Travel hotel booking room_selections total must match room_count")
        return self


class TravelVisitor(TimestampedBaseModel):
    firstName: str
    lastName: str
    type: Literal["adult", "child"] = "adult"


class TravelAttractionBookingAsset(AssetBase):
    kind: Literal["travel_attraction_booking"] = "travel_attraction_booking"
    app: Literal["Travel"] = "Travel"
    user_email: str
    attraction_name: str | None = None
    attraction_slug: str | None = None
    visit_date_ms: int
    adult_tickets: int = 1
    child_tickets: int = 0
    visitors: list[TravelVisitor] = Field(default_factory=list)
    booking_status: str = "confirmed"
    payment_status: str = "paid"
    payment_method: str = "card"
    currency: str = "USD"
    total_price: float | None = None
    booking_reference: str | None = None
    booked_at_ms: int | None = None

    @model_validator(mode="after")
    def validate_attraction_identity(self):
        if not (self.attraction_name or self.attraction_slug):
            raise ValueError("Travel attraction booking requires attraction_name or attraction_slug")
        if self.adult_tickets < 0 or self.child_tickets < 0:
            raise ValueError("Travel ticket counts must be non-negative")
        if self.adult_tickets + self.child_tickets <= 0:
            raise ValueError("Travel attraction booking requires at least one ticket")
        return self


class TravelFavoriteAsset(AssetBase):
    kind: Literal["travel_favorite"] = "travel_favorite"
    app: Literal["Travel"] = "Travel"
    user_email: str
    target: Literal["hotel", "attraction"]
    hotel_name: str | None = None
    hotel_slug: str | None = None
    attraction_name: str | None = None
    attraction_slug: str | None = None

    @model_validator(mode="after")
    def validate_target_identity(self):
        if self.target == "hotel":
            if not (self.hotel_name or self.hotel_slug):
                raise ValueError("Travel hotel favorite requires hotel_name or hotel_slug")
        elif self.target == "attraction":
            if not (self.attraction_name or self.attraction_slug):
                raise ValueError("Travel attraction favorite requires attraction_name or attraction_slug")
        return self


class TravelReviewAsset(AssetBase):
    kind: Literal["travel_review"] = "travel_review"
    app: Literal["Travel"] = "Travel"
    user_email: str
    target: Literal["flight", "hotel", "attraction"]
    rating: int
    comment: str
    from_airport: str | None = None
    to_airport: str | None = None
    departure_date_ms: int | None = None
    flight_code: str | None = None
    hotel_name: str | None = None
    hotel_slug: str | None = None
    attraction_name: str | None = None
    attraction_slug: str | None = None
    title: str | None = None
    visit_date_ms: int | None = None
    is_verified: bool = False

    @model_validator(mode="after")
    def validate_review(self):
        if self.rating < 1 or self.rating > 5:
            raise ValueError("Travel review rating must be between 1 and 5")
        if not self.comment.strip():
            raise ValueError("Travel review comment must be non-empty")
        if self.target == "flight":
            if not (self.from_airport and self.to_airport and self.departure_date_ms is not None):
                raise ValueError("Travel flight review requires from_airport, to_airport, and departure_date_ms")
        elif self.target == "hotel":
            if not (self.hotel_name or self.hotel_slug):
                raise ValueError("Travel hotel review requires hotel_name or hotel_slug")
        elif self.target == "attraction":
            if not (self.attraction_name or self.attraction_slug):
                raise ValueError("Travel attraction review requires attraction_name or attraction_slug")
        return self


class HmdpUserAsset(AssetBase):
    kind: Literal["hmdp_user"] = "hmdp_user"
    app: Literal["HMDP"] = "HMDP"
    phone: str
    password: str = "123456"
    user_id: int | None = None
    nick_name: str | None = None
    icon: str | None = "/hmdp/src/assets/imgs/icons/default-icon.png"
    city: str | None = None
    introduce: str | None = None
    fans: int = 0
    followee: int = 0
    gender: int = 0
    birthday: str | None = None
    credits: int = 0
    level: int = 0


class HmdpSessionAsset(AssetBase):
    kind: Literal["hmdp_session"] = "hmdp_session"
    app: Literal["HMDP"] = "HMDP"
    phone: str
    password: str = "123456"


class HmdpShopAsset(AssetBase):
    kind: Literal["hmdp_shop"] = "hmdp_shop"
    app: Literal["HMDP"] = "HMDP"
    name: str
    shop_id: int | None = None
    type_id: int | None = None
    type_name: str | None = "Food"
    images: list[str] = Field(default_factory=lambda: ["/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg"])
    area: str | None = None
    address: str = "Asset HMDP Address"
    x: float = 120.149993
    y: float = 30.334229
    avg_price: int = 50
    sold: int = 0
    comments: int = 0
    score: float = 4.8
    open_hours: str | None = "09:00-21:00"
    tags: list[str] = Field(default_factory=list)


class HmdpBlogAsset(AssetBase):
    kind: Literal["hmdp_blog"] = "hmdp_blog"
    app: Literal["HMDP"] = "HMDP"
    author_phone: str
    shop_name: str
    title: str
    content: str
    images: list[str] = Field(default_factory=list)
    expected_images: tuple[ImageContentExpectation, ...] = ()
    liked: int | None = None
    comments: int | None = None
    blog_id: int | None = None
    created_at_ms: int | None = None


class HmdpBlogCommentAsset(AssetBase):
    kind: Literal["hmdp_blog_comment"] = "hmdp_blog_comment"
    app: Literal["HMDP"] = "HMDP"
    blog_title: str
    blog_author_phone: str
    author_phone: str
    content: str
    liked: int = 0
    status: int = 0
    comment_id: int | None = None
    created_at_ms: int | None = None


class HmdpFollowAsset(AssetBase):
    kind: Literal["hmdp_follow"] = "hmdp_follow"
    app: Literal["HMDP"] = "HMDP"
    follower_phone: str
    following_phone: str


class HmdpShopFavoriteAsset(AssetBase):
    kind: Literal["hmdp_shop_favorite"] = "hmdp_shop_favorite"
    app: Literal["HMDP"] = "HMDP"
    user_phone: str
    shop_name: str


class HmdpShopReviewAsset(AssetBase):
    kind: Literal["hmdp_shop_review"] = "hmdp_shop_review"
    app: Literal["HMDP"] = "HMDP"
    user_phone: str
    shop_name: str
    content: str
    score: int = 5
    images: list[str] = Field(default_factory=list)
    liked: int = 0
    status: int = 0
    review_id: int | None = None
    created_at_ms: int | None = None


class HmdpBlogLikeAsset(AssetBase):
    kind: Literal["hmdp_blog_like"] = "hmdp_blog_like"
    app: Literal["HMDP"] = "HMDP"
    user_phone: str
    blog_title: str
    blog_author_phone: str


class HmdpVoucherAsset(AssetBase):
    kind: Literal["hmdp_voucher"] = "hmdp_voucher"
    app: Literal["HMDP"] = "HMDP"
    shop_name: str
    title: str
    voucher_id: int | None = None
    sub_title: str | None = None
    rules: str | None = None
    pay_value: int = 100
    actual_value: int = 500
    voucher_type: int = 1
    status: int = 1
    stock: int = 20
    init_stock: int | None = None
    allowed_levels: str | None = None
    min_level: int | None = None
    begin_time: str | None = "2026-01-01 00:00:00"
    end_time: str | None = "2027-01-01 00:00:00"


class HmdpVoucherOrderAsset(AssetBase):
    kind: Literal["hmdp_voucher_order"] = "hmdp_voucher_order"
    app: Literal["HMDP"] = "HMDP"
    user_phone: str
    shop_name: str
    voucher_title: str
    order_id: int | None = None
    pay_type: int = 1
    status: int = 1
    reconciliation_status: int = 1
    created_at_ms: int | None = None


Asset = Annotated[
    ContactAsset
    | SmsMessageAsset
    | AlarmAsset
    | CalendarEventAsset
    | DeviceFileAsset
    | ElementXUserAsset
    | ElementXSessionAsset
    | ElementXRoomAsset
    | ElementXMessageAsset
    | ElementXFileAsset
    | ElementXPollAsset
    | MailAccountAsset
    | MailMessageAsset
    | MattermostTeamAsset
    | MattermostChannelAsset
    | MattermostUserAsset
    | MattermostChannelMembershipAsset
    | MattermostPostAsset
    | MattermostFilePostAsset
    | MattermostSessionAsset
    | MattermostDirectChannelAsset
    | MattermostDirectPostAsset
    | MattermostReactionAsset
    | TempusPlaylistAsset
    | TempusFavoriteAsset
    | TempusUserAsset
    | TempusSessionAsset
    | MastodonAccountAsset
    | MastodonSessionAsset
    | MastodonStatusAsset
    | MastodonMediaStatusAsset
    | MastodonPollStatusAsset
    | MastodonFollowAsset
    | MastodonFavoriteAsset
    | MastodonReblogAsset
    | MastodonBookmarkAsset
    | MastodonPollVoteAsset
    | XiaoShiLiuUserAsset
    | XiaoShiLiuSessionAsset
    | XiaoShiLiuPostAsset
    | XiaoShiLiuCommentAsset
    | XiaoShiLiuLikeAsset
    | XiaoShiLiuCollectionAsset
    | XiaoShiLiuFollowAsset
    | XiaoShiLiuNotificationAsset
    | MallMemberAsset
    | MallSessionAsset
    | MallAddressAsset
    | MallProductAsset
    | MallBrandAsset
    | MallCartItemAsset
    | MallOrderAsset
    | MallReviewAsset
    | MeituanUserAsset
    | MeituanSessionAsset
    | MeituanRestaurantAsset
    | MeituanFoodAsset
    | MeituanAddressAsset
    | MeituanCartItemAsset
    | MeituanOrderAsset
    | MeituanCollectionAsset
    | MeituanCommentAsset
    | TravelUserAsset
    | TravelFlightBookingAsset
    | TravelHotelBookingAsset
    | TravelAttractionBookingAsset
    | TravelFavoriteAsset
    | TravelReviewAsset
    | HmdpUserAsset
    | HmdpSessionAsset
    | HmdpShopAsset
    | HmdpBlogAsset
    | HmdpBlogCommentAsset
    | HmdpFollowAsset
    | HmdpShopFavoriteAsset
    | HmdpShopReviewAsset
    | HmdpBlogLikeAsset
    | HmdpVoucherAsset
    | HmdpVoucherOrderAsset
    ,
    Field(discriminator="kind"),
]
ASSET_ADAPTER = TypeAdapter(Asset)
ASSET_LIST_ADAPTER = TypeAdapter(list[Asset])


def parse_asset(value: Asset | dict) -> Asset:
    return ASSET_ADAPTER.validate_python(value)


def parse_assets(values: list[Asset | dict]) -> list[Asset]:
    return ASSET_LIST_ADAPTER.validate_python(values)


def _materialize_binary_payload(source_path: str | None, text_content: str | None, content_b64: str | None, task_root: Path | None) -> str:
    if content_b64 is not None:
        return content_b64
    if source_path is not None:
        path = Path(source_path)
        if not path.is_absolute():
            if task_root is None:
                raise ValueError(f"Relative source_path requires task_root: {source_path}")
            path = task_root / path
        return base64.b64encode(path.read_bytes()).decode()
    return base64.b64encode((text_content or "").encode()).decode()


def _serialize_image_expectations(
    expectations: tuple[ImageContentExpectation, ...],
    task_root: Path | None,
) -> list[dict[str, Any]]:
    serialized = []
    for expectation in expectations:
        item = expectation.model_dump()
        item["content_b64"] = _materialize_binary_payload(
            expectation.source_path,
            None,
            expectation.content_b64,
            task_root,
        )
        item.pop("source_path", None)
        serialized.append(item)
    return serialized


def serialize_asset(asset: Asset, task_root: Path | None = None) -> dict:
    parsed = parse_asset(asset)
    if isinstance(parsed, DeviceFileAsset):
        payload = parsed.model_dump()
        payload["content_b64"] = _materialize_binary_payload(
            parsed.source_path,
            parsed.text_content,
            parsed.content_b64,
            task_root,
        )
        payload.pop("source_path", None)
        payload.pop("text_content", None)
        return payload
    if isinstance(parsed, ElementXFileAsset | MattermostFilePostAsset):
        payload = parsed.model_dump()
        payload["content_b64"] = _materialize_binary_payload(
            parsed.source_path,
            parsed.text_content,
            parsed.content_b64,
            task_root,
        )
        payload.pop("source_path", None)
        payload.pop("text_content", None)
        return payload
    if isinstance(parsed, MailMessageAsset):
        payload = parsed.model_dump()
        attachments = []
        for attachment in parsed.attachments:
            item = attachment.model_dump()
            item["content_b64"] = _materialize_binary_payload(
                attachment.source_path,
                attachment.text_content,
                attachment.content_b64,
                task_root,
            )
            item.pop("source_path", None)
            item.pop("text_content", None)
            attachments.append(item)
        payload["attachments"] = attachments
        return payload
    if isinstance(parsed, MastodonStatusAsset):
        payload = parsed.model_dump()
        media_attachments = []
        for attachment in parsed.media_attachments:
            item = attachment.model_dump()
            if any(value is not None for value in (attachment.source_path, attachment.text_content, attachment.content_b64)):
                item["content_b64"] = _materialize_binary_payload(
                    attachment.source_path,
                    attachment.text_content,
                    attachment.content_b64,
                    task_root,
                )
            item.pop("source_path", None)
            item.pop("text_content", None)
            media_attachments.append(item)
        payload["media_attachments"] = media_attachments
        return payload
    if isinstance(parsed, XiaoShiLiuPostAsset | HmdpBlogAsset):
        payload = parsed.model_dump()
        payload["expected_images"] = _serialize_image_expectations(
            parsed.expected_images,
            task_root,
        )
        return payload
    return parsed.model_dump()
