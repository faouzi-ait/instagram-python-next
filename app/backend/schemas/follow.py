from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class FollowResponse(BaseModel):
    user_id: int
    status: Literal["pending", "accepted"]


class FollowRequestResponse(BaseModel):
    follower_id: int
    username: str
    display_name: str | None
    avatar_url: str | None
    created_at: datetime


class FollowStatusResponse(BaseModel):
    user_id: int
    status: Literal["none", "pending", "accepted"]
    is_self: bool


class FollowUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    avatar_url: str | None
