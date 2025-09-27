import inspect
import sys
from enum import Enum as __enum


class QueueStatusEnum(str, __enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    DONE = "Done"
    FAILED = "Failed"
    IDLE = "Idle"


class APITagsEnum(str, __enum):
    WEBHOOK = "Webhook"

class APIServiceEnum(str, __enum):
    MICROSOFT = "MicrosoftGraphAPI"


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
