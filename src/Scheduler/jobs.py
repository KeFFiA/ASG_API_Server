import inspect
import sys
from datetime import datetime, timezone

from msgraph import GraphServiceClient

from API.FlightRadarAPI.LiveFlightsAPI import live_flights_adaptive
from API.Clients import MSGraphClient
from API.Utils import create_or_update_subscription, asg_regs_updater
from Config import setup_logger
from .PowerPlatformJobs import update_users_job, sync_engines_from_cirium
from Utils import DBProxy, next_quarter, next_ten_minutes
from .PowerPlatformJobs.Aircraft import update_aircraft_templates, update_aircrafts
from .PowerPlatformJobs.Airline import sync_airlines

logger = setup_logger("scheduler_processor")


async def update_subscription_job(db_proxy: DBProxy,
                                  client: GraphServiceClient | MSGraphClient = MSGraphClient(),
                                  change_type: str | None = None,
                                  resource: str | None = None,
                                  subscription_id: str | None = None,
                                  ttl: int = 60 * 65,
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
    {
        "id": "update_flightradar_flights",
        "name": "UpdateFlightradarFlights",
        "func": live_flights_adaptive,
        "trigger": "interval",
        "minutes": 10,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
    {
        "id": "update_microsoft_users",
        "name": "UpdateMicrosoftUsers",
        "func": update_users_job,
        "trigger": "interval",
        "minutes": 10,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
    {
        "id": "update_asg_regs",
        "name": "UpdateASGRegs",
        "func": asg_regs_updater,
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 9,
        "minute": 0,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
    {
        "id": "update_ac_types",
        "name": "UpdateACTypes",
        "func": update_aircraft_templates,
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 9,
        "minute": 5,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
    {
        "id": "update_engines",
        "name": "UpdateEngines",
        "func": sync_engines_from_cirium,
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 9,
        "minute": 5,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
    {
        "id": "update_airlines",
        "name": "UpdateAirlines",
        "func": sync_airlines,
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 9,
        "minute": 5,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
    {
        "id": "update_aircrafts",
        "name": "UpdateAircrafts",
        "func": update_aircrafts,
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 9,
        "minute": 10,
        "next_run_time": next_ten_minutes(datetime.now(timezone.utc)),
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 60,
    },
]

# TODO: fix

_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if
    (inspect.isclass(obj) or inspect.isfunction(obj) or inspect.isasyncgenfunction(obj)) and obj.__module__ == __name__
]
