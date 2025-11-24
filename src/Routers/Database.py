import random
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from pydantic.v1 import EmailStr
from sqlalchemy import select

from Config import RESPONSES_PATH, PA_APP_URL, CUSTOM_EXCEL_LEASE_HEADERS_ORDER
from Database.Models import Lease_Output
from Schemas import JsonFileSchema
from Schemas.Enums import service
from Utils import remove_file

router = APIRouter(
    prefix="/database",
    tags=["Database"]
)


@router.get('/{type}')
async def get_db(type: str, request: Request, background_tasks: BackgroundTasks):
    if type.lower() == 'lease_agr':
        main_db = await request.state.db.get_db("main")
        result = await main_db.execute(
            select(Lease_Output)
            .order_by(Lease_Output.id.asc())
        )

        rows = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Lease Agreements"

        headers = [column.key for column in Lease_Output.__table__.columns]

        formatted_headers = []
        for header in headers:
            formatted_header = header.replace('_', ' ').title()
            formatted_headers.append(formatted_header)

        # Добавляем заголовки
        ws.append(formatted_headers)

        # Добавляем данные
        for row in rows:
            ws.append([getattr(row, col_key, "") for col_key in headers])

        # Настраиваем ширину колонок
        for col_idx, col_name in enumerate(formatted_headers, start=1):
            max_len = len(col_name)
            for row_idx in range(2, len(rows) + 2):
                cell_value = ws.cell(row=row_idx, column=col_idx).value
                if cell_value is not None:
                    max_len = max(max_len, len(str(cell_value)))

            ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 2

        link_row = len(rows) + 3  # Сразу после данных
        ws.merge_cells(start_row=link_row, start_column=1, end_row=link_row, end_column=len(formatted_headers))

        cell = ws.cell(row=link_row, column=1, value="Back to app")
        cell.hyperlink = PA_APP_URL
        cell.font = Font(color="0000FF", underline="single")
        cell.alignment = Alignment(horizontal='center', vertical='center')

        filename_xl = "Lease_Agreements.xlsx"
        filepath_xl = RESPONSES_PATH / filename_xl
        wb.save(filepath_xl)
    else:
        filename_xl = "Lease_Agreements.xlsx"


    data = JsonFileSchema(
        type=type,
        user_email=EmailStr("integrator@ai12.com"),
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






