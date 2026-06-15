from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR
from gma.assets import ContactAsset, MailAccountAsset, MailMessageAsset, MallCartItemAsset, MallMemberAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists, AssetMissing
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row218-hp-author"
PRODUCT_SN = "fr0041TU"
EMILY_BEFORE = ContactAsset(name="Emily Parker", phone_number="+15552180218")
EMILY_AFTER = ContactAsset(name="Emily Parker", phone_number="+15552180218", email="789456@gmail.com")
MASON_CONTACT = ContactAsset(name="Mason Taylor", phone_number="+15552180219")
ACCOUNT = MailAccountAsset(display_name="Jordan Hayes", email="jordan.hayes@example.com")
EXPECTED_MAIL = MailMessageAsset(mailbox="sent", from_name=ACCOUNT.display_name, from_email="test@gmail.com", to=["789456@gmail.com"], subject="Laptop", body="Let's go shopping together next Wednesday, October 7, 2026; the items to purchase have already been confirmed.", read=True)
POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="HP Laptop Choice One", content="HP StarBook Pro 14-inch AI laptop is the laptop model I keep seeing recommended.", category="Technology", tags=["HP laptop"], image_urls=["/assets/contacts-xsl-hp-laptop-mall-mail-hp-probook-a.png"], min_image_count=1, created_at_ms=1790845800000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="HP Laptop Choice Two", content="Another student recommended HP StarBook Pro 14-inch AI laptop for daily work.", category="Technology", tags=["HP laptop"], image_urls=["/assets/contacts-xsl-hp-laptop-mall-mail-hp-probook-b.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="HP Laptop Choice Three", content="HP HyperX Omen PRO 16-inch gaming laptop is a stronger backup option.", category="Technology", tags=["HP laptop"], image_urls=["/assets/contacts-xsl-hp-laptop-mall-mail-hp-pavilion.png"], min_image_count=1, created_at_ms=1790845200000),
)

class ContactsXslHpLaptopMallMailTask(BaseTask):
    apps = {"Contacts", "XiaoShiLiu", "Mall", "Mail"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        EMILY_BEFORE,
        MASON_CONTACT,
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="HP Laptop Desk", email="hp.laptop.desk@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
        ACCOUNT,
    )
    goal = (
        "Open Contacts, add the email address 789456@gmail.com to Emily Parker, and delete Mason Taylor. Then open XiaoShiLiu, search for \"HP laptop\", "
        "identify the laptop model mentioned most often, and open Mall to add one matching laptop product to the cart. "
        "Finally open Mail and send an email to 789456@gmail.com with subject \"Laptop\" and body \"Let's go shopping together next Wednesday, October 7, 2026; the items to purchase have already been confirmed.\""
    )

    def criteria(self):
        return [
            AssetExists(EMILY_AFTER, task=self),
            AssetMissing(MASON_CONTACT, task=self),
            AssetExists(MallCartItemAsset(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, delete_status=False), task=self),
            AssetExists(EXPECTED_MAIL, task=self),
        ]
