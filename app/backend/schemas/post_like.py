from pydantic import BaseModel

class PostLikesResponse(BaseModel):
    post_id: int
    likes_count: int
    liked_by_me: bool