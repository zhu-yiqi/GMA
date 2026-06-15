from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class MessagesMarkUnreadThreadsReadTask(BaseTask):
    apps = {"Messages"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    maya_contact = ContactAsset(name="Maya Chen", phone_number="+15552011501")
    eli_contact = ContactAsset(name="Eli Carter", phone_number="+15552011502")
    ava_contact = ContactAsset(name="Ava Brooks", phone_number="+15552011503")
    read_contact = ContactAsset(name="Grace Miller", phone_number="+15552011504")

    maya_unread = SmsMessageAsset(
        address=maya_contact.phone_number,
        body="Can you confirm the studio key pickup?",
        box="inbox",
        read=False,
        timestamp_ms=202610010905,
    )
    eli_unread = SmsMessageAsset(
        address=eli_contact.phone_number,
        body="The courier window moved to 3 PM.",
        box="inbox",
        read=False,
        timestamp_ms=202610010915,
    )
    ava_unread = SmsMessageAsset(
        address=ava_contact.phone_number,
        body="Please check the revised seating note.",
        box="inbox",
        read=False,
        timestamp_ms=202610010925,
    )
    already_read = SmsMessageAsset(
        address=read_contact.phone_number,
        body="This thread was already handled yesterday.",
        box="inbox",
        read=True,
        timestamp_ms=202610010900,
    )

    maya_read = SmsMessageAsset(
        address=maya_contact.phone_number,
        body=maya_unread.body,
        box="inbox",
        read=True,
        timestamp_ms=maya_unread.timestamp_ms,
    )
    eli_read = SmsMessageAsset(
        address=eli_contact.phone_number,
        body=eli_unread.body,
        box="inbox",
        read=True,
        timestamp_ms=eli_unread.timestamp_ms,
    )
    ava_read = SmsMessageAsset(
        address=ava_contact.phone_number,
        body=ava_unread.body,
        box="inbox",
        read=True,
        timestamp_ms=ava_unread.timestamp_ms,
    )

    assets = (
        maya_contact,
        eli_contact,
        ava_contact,
        read_contact,
        already_read,
        maya_unread,
        eli_unread,
        ava_unread,
    )

    goal = "Open Messages and mark every unread text conversation as read."

    def criteria(self):
        return [
            AssetModified(self.maya_unread, self.maya_read, task=self),
            AssetModified(self.eli_unread, self.eli_read, task=self),
            AssetModified(self.ava_unread, self.ava_read, task=self),
        ]
