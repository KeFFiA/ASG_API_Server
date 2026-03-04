from typing import List, Optional

from sqlalchemy import select

from Database import ApplicationFont
from Schemas import FontsSchema, GetFontsResponseSchema


async def query_fonts(session, screen_size: Optional[int] = None) -> GetFontsResponseSchema:
    try:
        stmt = select(ApplicationFont)
        if screen_size:
            stmt = stmt.where(ApplicationFont.screen_size == screen_size)

        result = await session.execute(stmt)
        fonts: List[ApplicationFont] = result.scalars().all()

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