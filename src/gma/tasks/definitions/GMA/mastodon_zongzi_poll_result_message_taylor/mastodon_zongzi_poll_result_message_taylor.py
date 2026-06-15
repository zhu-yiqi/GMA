
from __future__ import annotations

from gma.assets import ContactAsset, MastodonAccountAsset, MastodonPollSpec, MastodonPollStatusAsset, MastodonPollVoteAsset, MastodonSessionAsset, MastodonStatusAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
POLL_TEXT = "Sweet zongzi or salty zongzi?"
WINNING_OPTION = "Sweet zongzi"
THANKS_TEXT = "Thanks for everyone's support."
TAYLOR_PHONE = "+15552021070"


class MastodonZongziPollResultMessageTaylorTask(BaseTask):
    apps = {"Mastodon", "Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    voter_a = MastodonAccountAsset(username="w2_row107_voter_a", email="w2.row107.a@example.com", display_name="Voter A")
    voter_b = MastodonAccountAsset(username="w2_row107_voter_b", email="w2.row107.b@example.com", display_name="Voter B")
    voter_c = MastodonAccountAsset(username="w2_row107_voter_c", email="w2.row107.c@example.com", display_name="Voter C")
    poll = MastodonPollStatusAsset(username=MAIN_USER, text=POLL_TEXT, visibility="public", poll=MastodonPollSpec(options=(WINNING_OPTION, "Salty zongzi"), multiple=False), created_at_ms=202609301000)
    vote_a = MastodonPollVoteAsset(voter_username="w2_row107_voter_a", poll_username=MAIN_USER, poll_text=POLL_TEXT, choices=(WINNING_OPTION,))
    vote_b = MastodonPollVoteAsset(voter_username="w2_row107_voter_b", poll_username=MAIN_USER, poll_text=POLL_TEXT, choices=(WINNING_OPTION,))
    vote_c = MastodonPollVoteAsset(voter_username="w2_row107_voter_c", poll_username=MAIN_USER, poll_text=POLL_TEXT, choices=("Salty zongzi",))
    taylor_contact = ContactAsset(name="Taylor", phone_number=TAYLOR_PHONE, phone_label="mobile")
    expected_reply = MastodonStatusAsset(username=MAIN_USER, text=THANKS_TEXT, visibility="public", reply_to_username=MAIN_USER, reply_to_text=POLL_TEXT)
    expected_sms = SmsMessageAsset(address=TAYLOR_PHONE, body=WINNING_OPTION, box="sent", read=True)
    expected_followup = SmsMessageAsset(address=TAYLOR_PHONE, body="Looks like what you like is also what others prefer.", box="sent", read=True)
    assets = (voter_a, voter_b, voter_c, poll, vote_a, vote_b, vote_c, taylor_contact, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon, check your previous poll post \"Sweet zongzi or salty zongzi?\", and determine which option has more votes. "
        "Add a comment under that poll with exactly \"Thanks for everyone's support.\" Then open Messages and send Taylor the winning option name exactly. "
        "If the first option wins, also send Taylor exactly \"Looks like what you like is also what others prefer.\""
    )

    def criteria(self):
        return [AssetExists(self.expected_reply, task=self), AssetExists(self.expected_sms, task=self), AssetExists(self.expected_followup, task=self)]
