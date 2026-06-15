from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateThreeEmailLabelsWorkTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    peter_before = ContactAsset(name="Peter Bennett", phone_number="5550101023", email="cvb@gmail.com", email_label="not work")
    peter_after = ContactAsset(name="Peter Bennett", phone_number="5550101023", email="cvb@gmail.com", email_label="work")
    liam_before = ContactAsset(name="Liam Carter", phone_number="5550101024", email="cxz@gmail.com", email_label="not work")
    liam_after = ContactAsset(name="Liam Carter", phone_number="5550101024", email="cxz@gmail.com", email_label="work")
    victor_before = ContactAsset(name="Victor Hayes", phone_number="5550101025", email="xsw@gmail.com", email_label="not work")
    victor_after = ContactAsset(name="Victor Hayes", phone_number="5550101025", email="xsw@gmail.com", email_label="work")
    assets = (peter_before, liam_before, victor_before)

    goal = (
        "Open Contacts and update these email labels to Work: Peter Bennett with \"cvb@gmail.com\", "
        "Liam Carter with \"cxz@gmail.com\", and Victor Hayes with \"xsw@gmail.com\"."
    )

    def criteria(self):
        return [
            AssetModified(self.peter_before, self.peter_after, task=self),
            AssetModified(self.liam_before, self.liam_after, task=self),
            AssetModified(self.victor_before, self.victor_after, task=self),
        ]
