from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import (
    DeviceFileAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
    MeituanAddressAsset,
    MeituanOrderAsset,
    MeituanOrderFood,
    MeituanSessionAsset,
    MeituanUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


PROTEST_TEXT = "Protest note: keep the Secret Shrimp Burger available for customers.\n"


class MailProtestLetterMeituanMcdonaldsOrderTask(BaseTask):
    apps = {"Mail", "Files", "Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Skyler Ross", email="skyler.ross@example.com")
    source_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="protest-letter.txt", mime_type="text/plain", source_path="assets/protest-letter.txt")
    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    meituan_session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    company_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name="Company",
        phone="5550101061",
        address="Company Campus",
        address_detail="Building A Front Desk",
        label="Office",
        gender="male",
        province="New York State",
        city=MEITUAN_LOGIN_CITY,
    )
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["fgh@gmail.com"],
        subject="Protest Letter",
        body="I do not agree with removing the Secret Shrimp Burger.",
        attachments=[MailAttachment(filename="protest-letter.txt", mime_type="text/plain", text_content=PROTEST_TEXT)],
        read=True,
    )
    expected_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name="McDonald's",
        foods=[
            MeituanOrderFood(food_name="Mai la Ji tui Bao single meal", quantity=1),
            MeituanOrderFood(food_name="French fries trio", quantity=1),
        ],
        status="Payment successful",
        address_name="Company",
        code=200,
        delivery_status=1,
    )
    assets = (account, source_file, meituan_user, meituan_session, company_address)

    goal = (
        "Open Mail and send an email to fgh@gmail.com with subject "
        '"Protest Letter", body "I do not agree with removing the Secret Shrimp Burger.", '
        "and attach the Downloads file \"protest-letter.txt\". Then open Meituan and order one "
        '"Mai la Ji tui Bao single meal" and one "French fries trio" from McDonald\'s '
        "for immediate delivery to the saved Company address. Pay with Alipay."
    )

    def criteria(self):
        return [AssetExists(self.expected_mail, task=self), AssetExists(self.expected_order, task=self)]
