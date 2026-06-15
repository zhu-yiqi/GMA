from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetDeleted, AssetExists, AssetModified
from gma.tasks.base import BaseTask


TAYLOR_MESSAGE = SmsMessageAsset(address="5550101100", body="Taylor message to remove.", box="inbox", read=True, timestamp_ms=202610010900)
UNREAD_BEFORE = SmsMessageAsset(address="5550101101", body="Please confirm this unread note.", box="inbox", read=False, timestamp_ms=202610010910)
UNREAD_AFTER = SmsMessageAsset(address="5550101101", body="Please confirm this unread note.", box="inbox", read=True, timestamp_ms=202610010910)
UNREAD_REPLY = SmsMessageAsset(address="5550101101", body="Received", box="sent", read=True)
HAYES_READ = SmsMessageAsset(address="5550101102", body="Hayes status already read.", box="inbox", read=True, timestamp_ms=202610010920)


class MessagesDeleteTaylorReplyUnreadLeaveHayesTask(BaseTask):
    apps = {"Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        ContactAsset(name="Taylor", phone_number="5550101100"),
        ContactAsset(name="Casey Unread", phone_number="5550101101"),
        ContactAsset(name="Hayes", phone_number="5550101102"),
        TAYLOR_MESSAGE,
        UNREAD_BEFORE,
        HAYES_READ,
    )
    goal = (
        "Open Messages and first delete Taylor's SMS conversation. Then check the unread message "
        "from Casey Unread and send exactly \"Received\" to that conversation. Finally, check Hayes's SMS; if it is already "
        "read, leave it alone, and if it is unread, send exactly \"I know\" to Hayes."
    )

    def criteria(self):
        return [
            AssetDeleted(TAYLOR_MESSAGE, task=self),
            AssetModified(UNREAD_BEFORE, UNREAD_AFTER, task=self),
            AssetExists(UNREAD_REPLY, task=self),
            AssetExists(HAYES_READ, task=self),
        ]
