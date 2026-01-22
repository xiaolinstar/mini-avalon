from .base import InfrastructureException


class RedisConnectionError(InfrastructureException):
    def __init__(self, message: str = "Redis 连接异常"):
        super().__init__(
            message=message,
            error_code="INFRA-REDIS-001"
        )

class DatabaseError(InfrastructureException):
    def __init__(self, message: str = "数据库操作异常"):
        super().__init__(
            message=message,
            error_code="INFRA-DB-001"
        )
