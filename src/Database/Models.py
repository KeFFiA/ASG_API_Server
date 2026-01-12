from .MainModels import *
from .ServiceModels import *
from .CiriumModels import *
from .AirlabsModels import *
from .FlightRadarModels import *

import inspect
import sys

# Add new models below
# ======================





# ======================

_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj)
]