from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ATTACHMENT_TEXT = "Plan two revision notes: update the opening summary and timeline.\n"


class MailDownloadMarch2AttachmentSendPlanTwoTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Morgan Lane", email="morgan.lane@example.com")
    older_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Dana Blake",
        from_email="dana.blake@example.com",
        to=[account.email],
        subject="February Proposal Notes",
        body="The February notes are attached for context.",
        attachments=[MailAttachment(filename="february-notes.txt", mime_type="text/plain", text_content="February proposal notes for reference.\n")],
        timestamp_ms=202603011000,
        read=True,
    )
    target_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Evan Price",
        from_email="evan.price@example.com",
        to=[account.email],
        subject="March 2 Plan Two Attachment",
        body="Please review the attached plan-two revision file from March 2.",
        attachments=[MailAttachment(filename="plan-two-revisions.txt", mime_type="text/plain", text_content=ATTACHMENT_TEXT)],
        timestamp_ms=202603021015,
        read=False,
    )
    newer_plain_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Harper Cole",
        from_email="harper.cole@example.com",
        to=[account.email],
        subject="March 3 Check-in",
        body="No attachment is needed for this check-in.",
        timestamp_ms=202603031100,
        read=False,
    )
    expected_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename="plan-two-revisions.txt",
        mime_type="text/plain",
        text_content=ATTACHMENT_TEXT,
    )
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["dfg@gmail.com"],
        subject="Plan Two",
        body="Minor revisions, please review.",
        attachments=[MailAttachment(filename="plan-two-revisions.txt", mime_type="text/plain", text_content=ATTACHMENT_TEXT)],
        read=True,
    )
    assets = (account, older_mail, target_mail, newer_plain_mail)

    goal = (
        "Open Mail, find the March 2 inbox email that has an attachment, and download "
        "that attachment to Downloads. Then send an email to dfg@gmail.com with subject "
        '"Plan Two", body "Minor revisions, please review.", and attach the downloaded file.'
    )

    def criteria(self):
        return [AssetExists(self.expected_file, task=self), AssetExists(self.expected_mail, task=self)]
