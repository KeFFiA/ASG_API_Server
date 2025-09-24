from typing import List, Optional

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
    status_description: Optional[str] = None
    progress: float


class StatusResponseSchema(BaseModel):
    user_email: str
    total: int
    processing_file: str
    processing_status: str
    processing_status_description: str
    progress: float
    data: List[ProgressFileSchema]