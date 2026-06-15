from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AnswerEquals, AssetDeleted, AssetExists, AssetModified
from gma.tasks.base import BaseTask


UNREAD_MESSAGES = (
    SmsMessageAsset(address="5550101103", body="Can you confirm the lobby handoff before lunch?", box="inbox", read=False, timestamp_ms=202610010900),
    SmsMessageAsset(address="5550101104", body="The loading dock entrance is closed today.", box="inbox", read=False, timestamp_ms=202610010910),
    SmsMessageAsset(address="5550101105", body="Please review the revised seating chart this morning.", box="inbox", read=False, timestamp_ms=202610010920),
)
READ_MESSAGES = tuple(
    SmsMessageAsset(address=message.address, body=message.body, box="inbox", read=True, timestamp_ms=message.timestamp_ms)
    for message in UNREAD_MESSAGES
)
EXPECTED_REPLY = SmsMessageAsset(address=UNREAD_MESSAGES[1].address, body="Received", box="sent", read=True)
TELEGRAM = SmsMessageAsset(address="5550101106", body="Telegram verification code: 421908", box="inbox", read=False, timestamp_ms=202610010930)
YOUTUBE = SmsMessageAsset(address="5550101107", body="YouTube verification code: 735612", box="inbox", read=False, timestamp_ms=202610010940)
EXPECTED_ANSWER = "Telegram: 421908; YouTube: 735612"


class MessagesReadReplyCodesDeleteThreadsTask(BaseTask):
    apps = {"Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        ContactAsset(name="Maya Chen", phone_number="5550101103"),
        ContactAsset(name="Owen Brooks", phone_number="5550101104"),
        ContactAsset(name="Nora Ellis", phone_number="5550101105"),
        ContactAsset(name="Telegram", phone_number="5550101106"),
        ContactAsset(name="YouTube", phone_number="5550101107"),
        *UNREAD_MESSAGES,
        TELEGRAM,
        YOUTUBE,
    )
    goal = (
        "Open Messages, mark the earliest three unread SMS conversations as read, then open the second-earliest of those conversations and send exactly \"Received\". "
        "Check the Telegram and YouTube verification codes and keep them for your final response. Delete only the Telegram and YouTube verification-code conversations; keep the other conversations. "
        "After deleting those code conversations, answer exactly in this format: \"Telegram: <code>; YouTube: <code>\"."
    )

    def criteria(self):
        return [
            AnswerEquals(EXPECTED_ANSWER),
            *(AssetModified(before, after, task=self) for before, after in zip(UNREAD_MESSAGES, READ_MESSAGES, strict=True)),
            AssetExists(EXPECTED_REPLY, task=self),
            AssetDeleted(TELEGRAM, task=self),
            AssetDeleted(YOUTUBE, task=self),
        ]
