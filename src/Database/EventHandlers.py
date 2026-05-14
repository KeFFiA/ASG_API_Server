from sqlalchemy import event

from Database import AircraftManual
import asyncio

from Scheduler.PowerPlatformJobs.Aircraft import update_create_aircraft_manual


@event.listens_for(AircraftManual, "after_insert")
@event.listens_for(AircraftManual, "after_update")
def manual_aircraft_changed(mapper, connection, target):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(update_create_aircraft_manual(target))
    except RuntimeError:
        raise RuntimeError("No running event loop")
