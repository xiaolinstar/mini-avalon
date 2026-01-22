import re

from src.utils.logger import get_logger
from src.wechat.commands import Command, CommandType

logger = get_logger(__name__)

class CommandParser:
    """
    Parses incoming WeChat text messages into structured Game Commands.
    Example inputs:
    - "建房" -> CREATE_ROOM
    - "/join 1234" -> JOIN_ROOM, args=["1234"]
    - "/pick 1 2 3" -> PICK_TEAM, args=["1", "2", "3"]
    - "投票 yes" -> VOTE, args=["yes"]
    """

    def __init__(self):
        # Map patterns to command types
        self.patterns = [
            # Pattern, CommandType
            (r'^建房$|^创建房间$', CommandType.CREATE_ROOM),
            (r'^/join\s+(\d+)$|^加入\s+(\d+)$', CommandType.JOIN_ROOM),
            (r'^/start$|^开始游戏$', CommandType.START_GAME),
            (r'^/nick\s+(.+)$|^昵称\s+(.+)$', CommandType.SET_NICKNAME),
            (r'^/status$|^状态$', CommandType.STATUS),
            (r'^/pick\s+([\d\s]+)$|^提议\s+([\d\s]+)$', CommandType.PICK_TEAM),
            (r'^/vote\s+(yes|no|赞成|反对)$|^投票\s+(yes|no|赞成|反对)$', CommandType.VOTE),
            (r'^/quest\s+(success|fail|成功|失败)$|^任务\s+(success|fail|成功|失败)$', CommandType.QUEST),
            (r'^/shoot\s+(\d+)$|^刺杀\s+(\d+)$', CommandType.SHOOT),
            (r'^/profile$|^我的战绩$|^战绩$', CommandType.PROFILE),
            (r'^/help$|^帮助$|^菜单$', CommandType.HELP),
        ]

    def parse(self, text: str, openid: str) -> Command:
        text = text.strip()
        logger.debug(f"Parsing text: {text} from {openid}")

        for pattern, cmd_type in self.patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                # Extract capture groups as arguments
                args = [g for g in match.groups() if g is not None]
                
                # Special handling for space-separated list of numbers (like in /pick)
                if cmd_type == CommandType.PICK_TEAM and args:
                    args = args[0].split()
                
                # Normalize common terms (e.g., '赞成' -> 'yes')
                args = [self._normalize_arg(a) for a in args]

                return Command(
                    command_type=cmd_type,
                    args=args,
                    raw_content=text,
                    user_openid=openid
                )

        return Command(
            command_type=CommandType.UNKNOWN,
            raw_content=text,
            user_openid=openid
        )

    def _normalize_arg(self, arg: str) -> str:
        mapping = {
            "赞成": "yes",
            "反对": "no",
            "成功": "success",
            "失败": "fail"
        }
        return mapping.get(arg, arg).lower()

# Singleton instance
parser = CommandParser()
