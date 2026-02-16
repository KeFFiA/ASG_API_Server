from .HealthCheck import router as health
from .Root import router as root
from .StatusCheck import router as status
from .Webhook import router as webhook
from .MSGraphRouters.UserInvite import router as invite_user
from .MSGraphRouters.User import router as user
from .Database import router as database
