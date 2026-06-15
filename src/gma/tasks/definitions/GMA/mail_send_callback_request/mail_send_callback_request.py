from __future__ import annotations

from gma.assets import MailAccountAsset, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MailSendCallbackRequestTask(BaseTask):
    apps = {"Mail"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(
        display_name="Morgan Lee",
        email="morgan.lee@example.com",
    )
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["aaa@gmail.com"],
        subject="",
        body="Please call back.",
        read=True,
    )
    assets = (account,)

    goal = (
        "Open Mail and send an email to aaa@gmail.com with a blank subject "
        "and exactly this body: \"Please call back.\""
    )

    def criteria(self):
        return [AssetExists(self.expected_mail, task=self)]
