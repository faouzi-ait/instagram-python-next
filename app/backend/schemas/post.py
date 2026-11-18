from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PostVisibility = Literal["public", "private"]


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str | None = Field(default=None, max_length=2200)
    visibility: PostVisibility = "public"


class PostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str | None = Field(default=None, max_length=2200)
    visibility: PostVisibility | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")

        if "visibility" in self.model_fields_set and self.visibility is None:
            raise ValueError("Visibility must be 'public' or 'private'.")

        return self


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    caption: str | None
    visibility: PostVisibility
    image_url: str
    image_width: int
    image_height: int
    created_at: datetime
    updated_at: datetime
