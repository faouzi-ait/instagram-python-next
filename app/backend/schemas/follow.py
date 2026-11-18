from typing import Literal

from pydantic import BaseModel

class FollowResponse(BaseModel):
    user_id: int
    status: Literal["pending", "accepted"]