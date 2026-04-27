"""Weather agent core module."""

import json
from urllib.parse import urlencode
from urllib.request import urlopen

from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool

SYSTEM_PROMPT = """你是一位擅长用双关语表达的专家天气预报员。

你可以使用三个工具：

- get_weather_for_coordinates：用于通过经纬度获取真实天气（优先）
- get_weather_for_location：用于获取特定地点的真实天气
- get_user_location：用于通过当前公网 IP 获取用户位置（最后兜底）

如果用户询问“我这里/当前位置”的天气，请优先使用 get_weather_for_coordinates。
如果没有可用经纬度，再考虑 get_user_location。"""


def _http_get_json(base_url: str, params: dict[str, str | int | float]) -> dict:
    """发送 GET 请求并返回 JSON 数据。"""
    url = f"{base_url}?{urlencode(params)}"
    with urlopen(url, timeout=10) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def _weather_code_to_text(code: int) -> str:
    mapping = {
        0: "晴朗",
        1: "大部晴朗",
        2: "局部多云",
        3: "阴天",
        45: "有雾",
        48: "有雾凇",
        51: "小毛雨",
        53: "中毛雨",
        55: "大毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        80: "阵雨",
        81: "中等阵雨",
        82: "强阵雨",
        95: "雷暴",
        96: "伴随小冰雹的雷暴",
        99: "伴随大冰雹的雷暴",
    }
    return mapping.get(code, f"未知天气代码({code})")


def _fetch_current_weather_by_coords(latitude: float, longitude: float) -> dict:
    weather_data = _http_get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
    )
    current = weather_data.get("current", {})
    if not current:
        raise ValueError("天气服务没有返回 current 字段")
    return current


def _format_weather_output(
    location_text: str,
    current: dict,
) -> str:
    weather_text = _weather_code_to_text(int(current.get("weather_code", -1)))
    return (
        f"{location_text} 当前天气：{weather_text}；"
        f"气温 {current.get('temperature_2m')}°C，"
        f"体感 {current.get('apparent_temperature')}°C，"
        f"湿度 {current.get('relative_humidity_2m')}%，"
        f"降水 {current.get('precipitation')} mm，"
        f"风速 {current.get('wind_speed_10m')} km/h。"
    )


@tool
def get_weather_for_coordinates(latitude: float, longitude: float) -> str:
    """通过经纬度获取真实天气（Open-Meteo API）。"""
    try:
        current = _fetch_current_weather_by_coords(latitude, longitude)
        return _format_weather_output(f"坐标({latitude}, {longitude})", current)
    except Exception as exc:
        return f"获取坐标天气失败：{exc}"


@tool
def get_weather_for_location(city: str) -> str:
    """获取指定城市的真实天气（Open-Meteo API）。"""
    try:
        geo_data = _http_get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": city, "count": 1, "language": "zh", "format": "json"},
        )
        results = geo_data.get("results", [])
        if not results:
            return f"未找到地点：{city}，请提供更精确的城市名称。"

        place = results[0]
        lat = place["latitude"]
        lon = place["longitude"]
        city_name = place.get("name", city)
        admin = place.get("admin1", "")
        country = place.get("country", "")
        current = _fetch_current_weather_by_coords(lat, lon)
        location_text = ", ".join(filter(None, [city_name, admin, country]))
        return _format_weather_output(location_text, current)
    except Exception as exc:
        return f"获取 {city} 天气失败：{exc}"

@tool
def get_user_location(runtime: ToolRuntime) -> str:
    """根据当前公网 IP 获取用户真实位置。"""
    try:
        data = _http_get_json("https://ipapi.co/json", {})
        if data.get("error"):
            return f"IP 定位失败：{data.get('reason', '未知错误')}"

        ip = data.get("ip", "未知IP")
        city = data.get("city", "")
        region = data.get("region", "")
        country_name = data.get("country_name", "")
        latitude = data.get("latitude", "")
        longitude = data.get("longitude", "")
        timezone = data.get("timezone", "")
        org = data.get("org", "")
        return (
            f"当前公网 IP: {ip}；位置：{city}, {region}, {country_name}；"
            f"坐标：({latitude}, {longitude})；时区：{timezone}；网络运营商：{org}。"
        )
    except Exception as exc:
        return f"获取用户位置失败：{exc}"

model = init_chat_model(
    "deepseek:deepseek-chat",
    temperature=0.5,
    timeout=10,
    max_tokens=1000,
)

# 这里使用 dataclass，但也支持 Pydantic 模型。
@dataclass
class ResponseFormat:
    """代理的响应模式。"""
    # 带双关语的回应（始终必需）
    punny_response: str
    # 天气的任何有趣信息（如果有）
    weather_conditions: str | None = None


agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_weather_for_coordinates, get_user_location, get_weather_for_location],
    response_format=ResponseFormat,
)

def run_weather_agent(
    user_message: str,
    thread_id: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    """Run weather agent with optional high-precision coordinates."""
    messages: list[dict[str, str]] = []
    if latitude is not None and longitude is not None:
        messages.append(
            {
                "role": "system",
                "content": (
                    "用户已授权高精度定位，请优先把以下坐标作为当前位置："
                    f"latitude={latitude}, longitude={longitude}。"
                    "如果需要查询“我这里的天气”，优先调用 get_weather_for_coordinates。"
                ),
            }
        )
    messages.append({"role": "user", "content": user_message})
    config = {"configurable": {"thread_id": thread_id}}
    return agent.invoke({"messages": messages}, config=config)
