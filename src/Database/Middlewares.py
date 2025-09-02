from sqlalchemy import event, select, update, func

from .Models import PDF_Queue


# Before inserting - assign a position
@event.listens_for(PDF_Queue, "before_insert")
def set_queue_position(mapper, connection, target):
    if target.queue_position is None:
        result = connection.execute(
            select(func.max(PDF_Queue.queue_position))
        )
        max_pos = result.scalar()
        target.queue_position = 1 if max_pos is None else max_pos + 1


# After deletion - recalculate the queue
@event.listens_for(PDF_Queue, "after_delete")
def reorder_queue(mapper, connection, target):
    if target.queue_position is not None:
        connection.execute(
            update(PDF_Queue)
            .where(PDF_Queue.queue_position > target.queue_position)
            .values(queue_position=PDF_Queue.queue_position - 1)
        )