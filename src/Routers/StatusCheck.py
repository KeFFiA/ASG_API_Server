import os
import random
from pathlib import Path

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from Database import PDF_Queue
from sqlalchemy import select

from Schemas import ProgressFileSchema, StatusResponseSchema, QueueStatusEnum

from Config import RESPONSES_PATH

router = APIRouter(
    prefix="/status",
    tags=["Status"]
)


def remove_file(path: str):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@router.get("/{email}")
async def status(email: str, request: Request, background_tasks: BackgroundTasks):
    db_service = await request.state.db.get_db("service")
    result = await db_service.execute(
        select(PDF_Queue)
        .where(PDF_Queue.user_email == email)
        .order_by(PDF_Queue.queue_position.asc())
    )
    rows = result.scalars().all()

    progress_list = [
        ProgressFileSchema(
            user_email=row.user_email,
            filename=row.filename,
            type=row.type,
            queue_position=row.queue_position,
            status=row.status,
            status_description=row.status_description,
            progress=round(row.progress, 2),
        )
        for row in rows
    ]

    if len(progress_list) == 0:
        total_progress = 0
    else:
        total_progress = round(sum(row.progress for row in rows) / len(progress_list), 2)
        if total_progress > 99:
            total_progress = 100


    processing = next((f for f in progress_list if f.status == QueueStatusEnum.PROCESSING), None)
    processing_file = processing.filename if processing else ""
    processing_status = processing.status if processing else QueueStatusEnum.IDLE
    processing_status_description = (
        processing.status_description if processing else "No files in queue"
    )

    data = StatusResponseSchema(
        user_email=email,
        total=len(progress_list),
        progress=total_progress,
        processing_file=processing_file,
        processing_status=processing_status,
        processing_status_description=processing_status_description,
        data=progress_list,
    )

    data_json = data.model_dump_json(indent=4)
    filename = f"{random.randint(10000, 99999)}.json"
    filepath = Path(RESPONSES_PATH / filename)
    filepath.write_text(data_json, encoding="utf-8")

    background_tasks.add_task(remove_file, str(filepath))

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=filename,
        background=background_tasks,
    )
