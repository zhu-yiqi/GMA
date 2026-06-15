from __future__ import annotations

from gma.assets import (
    ElementXMessageAsset,
    ElementXPollAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    MailAccountAsset,
    MailMessageAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


FIRST_ROOM = "Operations Lobby"
SECOND_ROOM = "Team Planning"
SECOND_ALIAS = "w5-row237-team-planning"
TEAM_MESSAGE = (
    "I think our team needs more people to support operations, so I plan to invite some new members. "
    "I will first invite Alex Parker, who was mentioned last time."
)
POLL_TITLE = "Do you agree to adding new members to the team?"
MAIL_BODY = "Alex Parker, regarding what we discussed last time, I hope you consider joining."
RECIPIENT = "alex.parker.team@gmail.com"


class ElementXMailTeamJoiningFollowupTask(BaseTask):
    apps = {"ElementX", "Mail"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    teammate = ElementXUserAsset(
        username="w5-row237-teammate",
        password="password",
        display_name="Team Planning Member",
    )
    first_room = ElementXRoomAsset(
        name=FIRST_ROOM,
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["w5-row237-teammate"],
        alias_localpart="w5-row237-operations-lobby",
        topic="Room to leave before continuing",
    )
    second_room = ElementXRoomAsset(
        name=SECOND_ROOM,
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["w5-row237-teammate"],
        alias_localpart=SECOND_ALIAS,
        topic="Team expansion planning",
    )
    account = MailAccountAsset(display_name="Jordan Miller", email="jordan.miller@example.com")
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[RECIPIENT],
        subject="Regarding Joining the Team",
        body=MAIL_BODY,
        read=True,
    )
    assets = (teammate, first_room, second_room, account)
    user_interaction = (
        "You are the user who asked the agent to email Alex Parker. If the agent asks for Alex Parker's "
        f"email address, respond: {RECIPIENT}. If the agent asks for unrelated information, do not respond."
    )

    goal = (
        f"Open ElementX, leave the room \"{FIRST_ROOM}\", then go to \"{SECOND_ROOM}\" and send exactly "
        f"\"{TEAM_MESSAGE}\". Create a poll titled \"{POLL_TITLE}\" with options \"Agree\" and \"Disagree\". "
        "Then open Mail and send an email to Alex Parker with subject \"Regarding Joining the Team\" "
        f"and body \"{MAIL_BODY}\"."
    )

    def criteria(self):
        return [
            AssetExists(
                ElementXMessageAsset(
                    room=SECOND_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=TEAM_MESSAGE,
                ),
                task=self,
            ),
            AssetExists(
                ElementXPollAsset(
                    room=SECOND_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    question=POLL_TITLE,
                    options=["Agree", "Disagree"],
                ),
                task=self,
            ),
            AssetExists(self.expected_mail, task=self),
        ]
