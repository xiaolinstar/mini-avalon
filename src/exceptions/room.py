from .base import DomainException


class RoomException(DomainException):
    pass

class RoomNotFoundError(RoomException):
    def __init__(self, room_id: str):
        super().__init__(
            message=f"未找到房间: {room_id}",
            error_code="ROOM-NOT_FOUND-001",
            details={"room_id": room_id}
        )

class RoomFullError(RoomException):
    def __init__(self, room_id: str):
        super().__init__(
            message="该房间已满",
            error_code="ROOM-STATE-001",
            details={"room_id": room_id}
        )

class RoomStateError(RoomException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code="ROOM-STATE-002"
        )
