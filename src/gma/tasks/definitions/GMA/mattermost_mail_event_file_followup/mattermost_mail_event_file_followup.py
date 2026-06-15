from __future__ import annotations

from gma.assets import (
    DeviceFileAsset,
    MailAccountAsset,
    MailMessageAsset,
    MailReplyReference,
    MattermostChannelAsset,
    MattermostFilePostAsset,
    MattermostSessionAsset,
    MattermostUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SENDER = "event-coordinator"
SECOND_CHANNEL = "event-followup"
FILE_NAME = "event-channel-notes.txt"
FILE_TEXT = "Event channel coordination notes for the team.\n"
MAIL_BODY = "Please join the channel and reply as soon as possible."
REPLY_BODY = "Okay"


class MattermostMailEventFileFollowupTask(BaseTask):
    apps = {"Mattermost", "Mail", "Files"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    sender = MattermostUserAsset(
        username=SENDER,
        email="event.coordinator@example.com",
        first_name="Event",
        last_name="Coordinator",
        team="company",
        channel_memberships=["event-planning", SECOND_CHANNEL],
    )
    first_channel = MattermostChannelAsset(
        team="company",
        name="event-planning",
        display_name="Event Planning",
        channel_type="O",
    )
    second_channel = MattermostChannelAsset(
        team="company",
        name=SECOND_CHANNEL,
        display_name="Event Follow-up",
        channel_type="O",
    )
    session = MattermostSessionAsset(username=SENDER)
    source_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename=FILE_NAME,
        mime_type="text/plain",
        text_content=FILE_TEXT,
    )
    expected_post = MattermostFilePostAsset(
        team="company",
        channel=SECOND_CHANNEL,
        username=SENDER,
        message="@all",
        filename=FILE_NAME,
        mime_type="text/plain",
        text_content=FILE_TEXT,
    )
    account = MailAccountAsset(display_name="Taylor Brooks", email="taylor.brooks@example.com")
    inbound = MailMessageAsset(
        mailbox="inbox",
        from_name="Nora Fields",
        from_email="unread.event.sender@example.com",
        to=[account.email],
        subject="Unread event follow-up",
        body="Please confirm you received the event notice.",
        read=False,
    )
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["lihua@gmail.com"],
        subject="event",
        body=MAIL_BODY,
        read=True,
    )
    expected_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[inbound.from_email],
        subject="RE: Unread event follow-up",
        body=REPLY_BODY,
        read=True,
        reply_to=MailReplyReference(from_email=inbound.from_email, subject=inbound.subject),
    )
    assets = (first_channel, second_channel, sender, session, source_file, account, inbound)

    goal = (
        "Open Mattermost as event-coordinator, go to the channel \"Event Follow-up\", "
        f"send exactly \"@all\" and attach \"{FILE_NAME}\" from Downloads. Then open Mail and send "
        f"lihua@gmail.com an email with subject \"event\" and body \"{MAIL_BODY}\". "
        f"After that, find the unread email titled \"Unread event follow-up\" and reply exactly \"{REPLY_BODY}\"."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_post, task=self),
            AssetExists(self.expected_mail, task=self),
            AssetExists(self.expected_reply, task=self),
        ]
