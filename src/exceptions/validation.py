from .base import ValidationException


class ParamValidationError(ValidationException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code="VALIDATION-PARAM-001",
            details=details
        )

class InvalidCommandError(ValidationException):
    def __init__(self, command: str):
        super().__init__(
            message=f"无效的指令: {command}",
            error_code="VALIDATION-CMD-001",
            details={"command": command}
        )
