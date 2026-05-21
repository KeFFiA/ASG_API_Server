from typing import Optional
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel

from Schemas.decorators import exactly_one_of
from Schemas.Enums import OSType


class GetApplicationIdQuery(BaseModel):
    application_id: Optional[UUID] = Query(default=None, description="Application ID")


class GetApplicationSizeQuery(BaseModel):
    screen_size: Optional[int] = Query(default=None, description="Screen size")


class DeviceInfo(BaseModel):
    os_type: OSType
    screen_size: int = Query(description="Screen size")


@exactly_one_of('file_name', 'file_id')
class GetApplicationFileQuery(BaseModel):
    file_name: Optional[str] = Query(None, description="File name")
    file_id: Optional[int] = Query(None, description="File ID")