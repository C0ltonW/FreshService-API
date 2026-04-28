from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FreshRequester(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = Field(default=None)
    location: Optional[str] = None


class FreshConversation(BaseModel):
    """
    Represents a single conversation or note on a Freshservice ticket.

    Freshservice uses both 'public' and 'private' concepts depending on context.
    """

    id: int
    body: Optional[str] = None
    body_text: Optional[str] = None
    public: Optional[bool] = None
    user_id: Optional [int]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FreshTicket(BaseModel):
    """
    Pydantic model representing a Freshservice ticket.

    This model intentionally allows optional and partially populated fields
    to accommodate different Freshservice endpoints and account configurations.

    Notes:
    - Conversations are not included by default and may be empty
    - custom_fields are preserved as a raw dictionary
    """
    id: int
    description: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[int] = None
    source: Optional[int] = None
    type: Optional[str] = None
    urgency: Optional[int] = Field(default=None)
    impact: Optional[int] = Field(default=None)
    group_id: Optional[int] = None
    department_id: Optional[int] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    requester_id: Optional [int] = None
    requester: Optional[FreshRequester] = Field(default=None)
    location: Optional[str] = Field(default=None)
    subject: str
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    conversations: List[FreshConversation] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


    @property
    def is_open(self) -> bool:
        return self.status in (2, 3)

    @property
    def is_closed(self) -> bool:
        return self.status in (4, 5)

