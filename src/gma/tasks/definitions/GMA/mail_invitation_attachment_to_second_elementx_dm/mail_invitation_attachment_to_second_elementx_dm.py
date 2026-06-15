from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import (
    DeviceFileAsset,
    ElementXFileAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


INVITATION_TEXT = "Tomorrow invitation details: arrive at 6:30 PM and bring your badge.\n"
OLDER_INVITATION_TEXT = "Older invitation details for last week's event.\n"
FIRST_CONTACT = "w2-row97-avery"
SECOND_CONTACT = "w2-row97-blake"
SECOND_CONTACT_ID = elementx_user_id(SECOND_CONTACT)


class MailInvitationAttachmentToSecondElementXDmTask(BaseTask):
    apps = {"Mail", "Files", "ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Parker Lee", email="parker.lee@example.com")
    older_invitation = MailMessageAsset(
        mailbox="inbox",
        from_name="Events Team",
        from_email="events.old@example.com",
        to=[account.email],
        subject="Old Invitation Attachment",
        body="The older invitation is attached.",
        attachments=[MailAttachment(filename="old-invitation.txt", mime_type="text/plain", text_content=OLDER_INVITATION_TEXT)],
        timestamp_ms=202609301000,
        read=True,
    )
    target_invitation = MailMessageAsset(
        mailbox="inbox",
        from_name="Events Team",
        from_email="events.team@example.com",
        to=[account.email],
        subject="Tomorrow Invitation Attachment",
        body="The invitation for tomorrow is attached.",
        attachments=[MailAttachment(filename="tomorrow-invitation.txt", mime_type="text/plain", text_content=INVITATION_TEXT)],
        timestamp_ms=202610011000,
        read=False,
    )
    first_user = ElementXUserAsset(username=FIRST_CONTACT, password="password", display_name="Avery Miles")
    second_user = ElementXUserAsset(username=SECOND_CONTACT, password="password", display_name="Blake Turner")
    first_dm = ElementXRoomAsset(name="Avery Miles", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[FIRST_CONTACT], created_at_ms=202610011010)
    second_dm = ElementXRoomAsset(name="Blake Turner", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[SECOND_CONTACT], created_at_ms=202610011020)
    expected_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="tomorrow-invitation.txt", mime_type="text/plain", text_content=INVITATION_TEXT)
    expected_elementx_file = ElementXFileAsset(room=SECOND_CONTACT_ID, sender_username="testuser", sender_password="testpass123", filename="tomorrow-invitation.txt", mime_type="text/plain", text_content=INVITATION_TEXT)
    expected_elementx_message = ElementXMessageAsset(room=SECOND_CONTACT_ID, sender_username="testuser", sender_password="testpass123", text="This is tomorrow's invitation, please check.")
    assets = (account, older_invitation, target_invitation, first_user, second_user, first_dm, second_dm)

    goal = (
        "Open Mail, find the newest inbox email with an invitation attachment, and download that attachment "
        "to Downloads. Then open ElementX, go to the direct chat with Blake Turner, send the downloaded attachment "
        'there, and send exactly "This is tomorrow\'s invitation, please check."'
    )

    def criteria(self):
        return [AssetExists(self.expected_file, task=self), AssetExists(self.expected_elementx_file, task=self), AssetExists(self.expected_elementx_message, task=self)]
