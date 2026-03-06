import inspect
import sys
from enum import Enum as __enum

class FlightStatusEnum(str, __enum):
    SCHEDULED = "scheduled"
    EN_ROUTE = "en-route"
    LANDED = "landed"


class UpsertStatusEnum(str, __enum):
    UPDATED = "Updated"
    CREATED = "Created"


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
