from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Database import Font, Application
from Schemas import OSType
from Schemas.PowerPlatform.DefaultSchemas import FontSchema, ApplicationSchema
from Schemas.PowerPlatform.QuerySchemas.ApplicationSchemas import GetApplicationIdQuery, DeviceInfo
from Utils import map_asset


async def query_apps(session: AsyncSession, _payload: GetApplicationIdQuery) -> List[ApplicationSchema]:
    payload = GetApplicationIdQuery(
        **_payload.model_dump()
    )

    try:
        stmt = (
            select(Application)
            .options(
                selectinload(Application.asset)
            )
        )
        if payload.application_id:
            stmt = stmt.where(Application.application_id == payload.application_id)

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
                )
            )

        return apps_list
    except Exception as _ex:
        raise _ex



async def query_fonts(session: AsyncSession, _payload: DeviceInfo) -> List[FontSchema]:
    payload = DeviceInfo(
        **_payload.model_dump()
    )

    try:
        stmt = select(Font)
        if payload.screen_size:
            stmt = stmt.where(Font.screen_size == payload.screen_size)

        result = await session.execute(stmt)
        fonts = result.scalars().all()

        fonts_list = []


        if payload.os_type not in {OSType.IOS, OSType.ANDROID}:
            fonts_list.append(
                FontSchema(
                    font_name=font.font_name,
                    font_size=font.font_size,
                    screen_size=font.screen_size,
                    usage_name=font.usage_name,
                    font_color=font.font_color,
                    font_weight=font.font_weight
                )
                for font in fonts
            )
        else:
            fonts_list.append(
                FontSchema(
                    font_name=font.font_name,
                    font_size=font.font_size_alternative,
                    screen_size=font.screen_size,
                    usage_name=font.usage_name,
                    font_color=font.font_color,
                    font_weight=font.font_weight
                )
                for font in fonts
            )

        return fonts_list
    except Exception as _ex:
        raise _ex