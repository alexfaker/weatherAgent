from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的问题")
    thread_id: str = Field(default="wx-default-thread", description="会话 ID")
    latitude: float | None = Field(default=None, description="用户纬度")
    longitude: float | None = Field(default=None, description="用户经度")


class ChatResponse(BaseModel):
    thread_id: str
    punny_response: str
    weather_conditions: str | None = None
    raw: dict
