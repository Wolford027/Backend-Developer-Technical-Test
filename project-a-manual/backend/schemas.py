from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None

class NoteCreate(NoteBase):
    pass

class NoteUpdate(NoteBase):
    title: Optional[str] = None
    content: Optional[str] = None

class NoteOut(NoteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)