import inspect
import sys

from msgraph import GraphServiceClient
from API.Clients import MSGraphClient
from API.Utils import create_or_update_subscription
from Config import setup_logger
from Utils import DBProxy

logger = setup_logger("scheduler_processor")


async def update_subscription_job(db_proxy: DBProxy,
                                    client: GraphServiceClient | MSGraphClient = MSGraphClient(),
                                    change_type: str | None = None,
                                    resource: str | None = None,
                                    subscription_id: str | None = None,
                                    ttl:int = 60*65,
                                    ) -> bool:
    """
    !!DON'T USE IN THE SCHEDULER!!

    Update or create subscription for users updates

    :param resource: Resource name(e.g. users)
    :param change_type: Tracked action(e.g. created, updated)
    :param db_proxy: DBProxy(request.state.db) object
    :param ttl: Time to live (in seconds) for new subscriptions record
    :param subscription_id: Webhook Subscription ID(UUID)
    :param client: GraphServiceClient object
    :return: bool
    """
    try:
        logger.info("Running subscription update job...")
        if change_type is None:
            change_type = "created"
        if resource is None:
            resource = "users"

        await create_or_update_subscription(db_proxy=db_proxy,
                                            graph_client=client,
                                            change_type=change_type,
                                            resource=resource,
                                            subscription_id=subscription_id,
                                            ttl=ttl)
        logger.info("Subscription update job done")
        return True
    except Exception as _ex:
        logger.error(f"Subscription update job failed: {_ex}")
        return False



jobs = [
    # {
    #     "name": "update_subscription_job_users",
    #     "func": update_subscription_job_users,
    #     "args": [client],
    #     "trigger": "interval",
    #     "days": 3,
    #     "next_run_time": None
    # }
]

_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isclass(obj) or inspect.isfunction(obj) or inspect.isasyncgenfunction(obj)) and obj.__module__ == __name__
]
