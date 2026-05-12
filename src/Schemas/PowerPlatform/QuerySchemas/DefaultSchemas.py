from typing import Optional

from fastapi import Query
from pydantic import BaseModel, EmailStr


class GetUserSchemaQuery(BaseModel):
    user_email: EmailStr = Query(..., description="Email of the user")


class GetSumPolicyQuery(BaseModel):
    aircraft_id: int = Query(..., description="Aircraft ID")
    is_hd: Optional[bool] = Query(default=False, description="Is HD?")
    is_hw: Optional[bool] = Query(default=False, description="Is HW?")
    is_hsl: Optional[bool] = Query(default=False, description="Is HSL?")

