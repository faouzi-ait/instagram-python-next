from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    website_url: str | None
    is_private: bool
    is_email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime