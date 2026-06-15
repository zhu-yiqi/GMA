from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AnswerEquals
from gma.tasks.base import BaseTask


VOLC_CODE = "983276"
DIANPING_CODE = "874221"
EXPECTED = "9832"


class MessagesAnswerLargestVerificationPrefixTask(BaseTask):
    apps = {"Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        ContactAsset(name="VolcEngine", phone_number="5550101096"),
        ContactAsset(name="Dianping", phone_number="5550101097"),
        SmsMessageAsset(address="5550101096", body=f"VolcEngine verification code: {VOLC_CODE}", box="inbox", read=False, timestamp_ms=202610010900),
        SmsMessageAsset(address="5550101097", body=f"Dianping verification code: {DIANPING_CODE}", box="inbox", read=False, timestamp_ms=202610010910),
    )
    goal = (
        "Open Messages and check the latest verification codes from VolcEngine and Dianping. "
        "Find the numerically larger code and answer with only the first 4 digits of that code."
    )

    def criteria(self):
        return [AnswerEquals(EXPECTED)]
