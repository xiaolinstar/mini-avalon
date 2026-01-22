from dataclasses import dataclass


@dataclass
class BaseGameException(Exception):
    message: str
    error_code: str
    details: dict | None = None
    cause: Exception | None = None

    def __str__(self):
        return f"[{self.error_code}] {self.message}"

class DomainException(BaseGameException):
    pass

class InfrastructureException(BaseGameException):
    pass

class ValidationException(BaseGameException):
    pass
