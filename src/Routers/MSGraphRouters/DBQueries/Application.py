from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Database import Font, Application
from Schemas import FontsSchema, GetFontsResponseSchema, ApplicationSchema
from Utils import map_asset


async def query_apps(session: AsyncSession, application_id: Optional[UUID]):
    try:
        stmt = (
            select(Application)
            .options(
                selectinload(Application.asset)
            )
        )
        if application_id:
            stmt = stmt.where(Application.application_id == application_id)

        result = await session.execute(stmt)
        apps = result.scalars().all()

        apps_list = []

        for app in apps:
            apps_list.append(
                ApplicationSchema(
                    application_id=app.application_id,
                    application_name=app.application_name,
                    application_description=app.application_description,
                    application_status=app.status,
                    asset=map_asset(app.asset)
                ).model_dump(mode="json")
            )

        return apps_list
    except Exception as _ex:
        raise _ex




async def query_fonts(session: AsyncSession, screen_size: Optional[int] = None) -> GetFontsResponseSchema:
    try:
        stmt = select(Font)
        if screen_size:
            stmt = stmt.where(Font.screen_size == screen_size)

        result = await session.execute(stmt)
        fonts = result.scalars().all()

        fonts_list = []
        for font in fonts:
            fonts_list.append(
                FontsSchema(
                    font_name=font.font_name,
                    font_size=font.font_size,
                    screen_size=font.screen_size,
                    usage_name=font.usage_name,
                    font_color=font.font_color,
                    font_weight=font.font_weight
                )
            )

        return GetFontsResponseSchema(font=fonts_list).model_dump(mode="json")
    except Exception as _ex:
        raise _ex