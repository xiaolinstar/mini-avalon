from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class CommandType(Enum):
    CREATE_ROOM = "create_room"
    JOIN_ROOM = "join_room"
    START_GAME = "start_game"
    SET_NICKNAME = "set_nickname"
    STATUS = "status"
    PICK_TEAM = "pick_team"
    VOTE = "vote"
    QUEST = "quest"
    SHOOT = "shoot"  # Assassination
    PROFILE = "profile"
    HELP = "help"
    UNKNOWN = "unknown"

class Command(BaseModel):
    command_type: CommandType
    args: list[str] = []
    raw_content: str
    user_openid: str

    @property
    def room_id(self) -> str | None:
        """Convenience helper for commands that include a room ID."""
        if self.command_type == CommandType.JOIN_ROOM and len(self.args) > 0:
            return self.args[0]
        return None
