from typing import Optional

from pydantic import BaseModel


class FreshAgent(BaseModel):
    id: int
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    active: Optional[bool] = None
