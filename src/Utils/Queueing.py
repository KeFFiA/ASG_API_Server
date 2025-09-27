from sqlalchemy import select, func, delete, update
from pydantic import EmailStr

from Database.Models import PDF_Queue


async def add_to_queue(session, filename: str, user_email: EmailStr, _type: str):
    """
    Adds file to queue

    :param session: SQLAlchemy async session
    :param filename: file name
    :param user_email: user email
    :param _type: type of file(e.g. Claims)

    :return: PDF_Queue row object
    """
    result = await session.execute(select(func.max(PDF_Queue.queue_position)))
    max_pos = result.scalar()
    next_pos = 1 if max_pos is None else max_pos + 1

    row = PDF_Queue(
        filename=filename,
        user_email=user_email,
        type=_type,
        queue_position=next_pos
    )
    session.add(row)

    return row


async def remove_from_queue(session, row_id: int) -> bool:
    """
    Removes an entry from the queue by id and shifts all positions after it by -1.

    :param session: SQLAlchemy async session
    :param row_id: id of the entry
    :return: True if the entry was found and removed
    """

    result = await session.execute(
        select(PDF_Queue).where(PDF_Queue.id == row_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False

    deleted_pos = row.queue_position

    await session.execute(delete(PDF_Queue).where(PDF_Queue.id == row_id))

    await session.execute(
        update(PDF_Queue)
        .where(PDF_Queue.queue_position > deleted_pos)
        .values(queue_position=PDF_Queue.queue_position - 1)
    )

    return True

__all__ = ["add_to_queue", "remove_from_queue"]
