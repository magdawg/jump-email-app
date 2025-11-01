from pydantic import BaseModel
from datetime import datetime


class CategoryCreate(BaseModel):
    name: str
    description: str


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str
    email_count: int = 0


class EmailResponse(BaseModel):
    id: int
    gmail_message_id: str
    subject: str
    sender: str
    summary: str
    received_at: datetime


class GmailAccountResponse(BaseModel):
    id: int
    email: str
    is_primary: bool
