from .base import DomainException


class GameException(DomainException):
    pass

class NotLeaderError(GameException):
    def __init__(self):
        super().__init__(
            message="你不是当前队长，无法执行此操作",
            error_code="GAME-AUTH-001"
        )

class InvalidPhaseError(GameException):
    def __init__(self, expected_phase: str, current_phase: str):
        super().__init__(
            message=f"当前阶段为 {current_phase}，无法执行此操作（需求: {expected_phase}）",
            error_code="GAME-STATE-001",
            details={"expected": expected_phase, "current": current_phase}
        )

class PlayerNotInGameError(GameException):
    def __init__(self, openid: str):
        super().__init__(
            message="你不在当前游戏中",
            error_code="GAME-AUTH-002",
            details={"openid": openid}
        )
