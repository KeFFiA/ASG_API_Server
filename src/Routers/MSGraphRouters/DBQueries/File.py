from base64 import b64decode, b64encode
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from Database import Asset
from Schemas import GetFileResponseSchema


async def query_load_file(session: AsyncSession, file_name: str, file_description: Optional[str], file_data: str):
    try:
        header, encoded = file_data.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")
        decoded_bytes = b64decode(encoded)

        file = Asset(
            asset_name=file_name,
            asset_description=file_description,
            mime_type=mime_type,
            base64=decoded_bytes
        )

        session.add(file)
        await session.commit()

    except Exception as _ex:
        raise _ex


async def query_file(session: AsyncSession, file_name: Optional[str], file_id: Optional[int]) -> GetFileResponseSchema | None:
    try:
        stmt = select(Asset)
        if file_name:
            stmt = stmt.where(Asset.asset_name == file_name)
        if file_id:
            stmt = stmt.where(Asset.id == file_id)

        result = await session.execute(stmt)
        file: Asset = result.scalars().one_or_none()

        if not file:
            return None
        encoded = b64encode(file.base64).decode()
        data_uri = f"data:{file.mime_type};base64,{encoded}"

        return GetFileResponseSchema(file_name=file.asset_name, file_description=file.asset_description,
                                     file_data=data_uri).model_dump(mode="json")

    except Exception as _ex:
        raise _ex
