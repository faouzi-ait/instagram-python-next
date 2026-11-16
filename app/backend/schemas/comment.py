from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

CommentContent = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=2200,
    ),
]

class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: CommentContent

class CommentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: CommentContent

class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    updated_at: datetime