from fastapi import FastAPI, HTTPException

from app.schemas import ChatRequest, ChatResponse
from src.agent import run_weather_agent

app = FastAPI(title="Weather Agent API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if (req.latitude is None) ^ (req.longitude is None):
        raise HTTPException(status_code=400, detail="latitude 和 longitude 必须同时提供")

    try:
        result = run_weather_agent(
            user_message=req.message,
            thread_id=req.thread_id,
            latitude=req.latitude,
            longitude=req.longitude,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"agent 调用失败: {exc}") from exc

    structured = result.get("structured_response")
    if structured is None:
        raise HTTPException(status_code=500, detail="agent 未返回 structured_response")

    return ChatResponse(
        thread_id=req.thread_id,
        punny_response=getattr(structured, "punny_response", ""),
        weather_conditions=getattr(structured, "weather_conditions", None),
        raw=result,
    )
