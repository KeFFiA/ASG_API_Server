import inspect
import sys
from enum import Enum as __enum


class InvitationStatusEnum(str, __enum):
    PENDING_ACCEPTANCE = "PendingAcceptance"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    ERROR = "Error"

    @property
    def code(self) -> int:
        mapping = {
            InvitationStatusEnum.PENDING_ACCEPTANCE: 0,
            InvitationStatusEnum.IN_PROGRESS: 1,
            InvitationStatusEnum.COMPLETED: 2,
            InvitationStatusEnum.ERROR: 3,
        }
        return mapping[self]

    @classmethod
    def from_api(cls, value: str) -> int:
        """Converts a string from an API into a numeric code"""
        try:
            return cls(value).code
        except ValueError:
            raise ValueError(f"Unknown invitation status: {value}")


class UserTypesEnum(str, __enum):
    GUEST = "Guest"
    MEMBER = "Member"




_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]

