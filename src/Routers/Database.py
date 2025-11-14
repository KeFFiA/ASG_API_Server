import random
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from openpyxl.workbook import Workbook
from sqlalchemy import select

from Config import RESPONSES_PATH
from Database.Models import Lease_Outputs
from Schemas import JsonFileSchema
from Schemas.Enums import service
from Utils import remove_file

router = APIRouter(
    prefix="/database",
    tags=["Database"]
)

@router.get('/{email}/{type}')
async def get_db(email: Optional[str], type: str, request: Request, background_tasks: BackgroundTasks):
    if type.lower() == 'lease_agr':
        main_db = await request.state.db.get_db("main")
        result = await main_db.execute(
            select(Lease_Outputs)
            .order_by(Lease_Outputs.id.asc())
        )

        rows = await result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Lease Agreements"
        headers = Lease_Outputs.__table__.columns.keys()
        ws.append(headers)
        for row in rows:
            ws.append([getattr(row, col) for col in headers])
        filename_xl = "Lease_Agreements.xlsx"
        filepath_xl = RESPONSES_PATH / filename_xl
        wb.save(filepath_xl)
        background_tasks.add_task(remove_file, str(filepath_xl))
    else:
        filename_xl = "Lease_Agreements.xlsx"


    data = JsonFileSchema(
        type=type,
        user_email=email,
        filename=filename_xl
    )

    filename = f"{random.randint(10000, 99999)}.json"
    filepath = Path(RESPONSES_PATH / filename)
    filepath.write_text(data.model_dump_json(indent=4), encoding="utf-8")

    background_tasks.add_task(remove_file, str(filepath))

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=filename,
        background=background_tasks,
    )






