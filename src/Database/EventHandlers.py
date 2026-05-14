from sqlalchemy import event

from Database import AircraftManual
import asyncio


@event.listens_for(AircraftManual, "after_insert")
@event.listens_for(AircraftManual, "after_update")
def manual_aircraft_changed(mapper, connection, target):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(...)
    except RuntimeError:
        raise RuntimeError("No running event loop")
