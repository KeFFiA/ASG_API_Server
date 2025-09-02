from typing import List

from pydantic import BaseModel, EmailStr

class JsonFileSchema(BaseModel):
    user_email: EmailStr
    filename: str
    type: str


class ProgressFileSchema(BaseModel):
    user_email: EmailStr
    filename: str
    type: str
    queue_position: int
    status: str


class StatusResponseSchema(BaseModel):
    user_email: str
    total: int
    processing_file: str
    processing_status: str
    data: List[ProgressFileSchema]