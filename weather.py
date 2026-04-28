# ============================================================
# weather.py — Open-Meteo Weather API Integration
# ============================================================
# Two-step process:
#   1. Geocode the location name → latitude/longitude
#   2. Fetch weather forecast for those coordinates
#
# Uses Open-Meteo (100% free, no API key required).
# ============================================================

import httpx
from config import OPEN_METEO_URL, GEOCODE_URL


async def geocode_location(place_name: str) -> dict | None:
    """
    Convert a place name (village/city) to lat/lon coordinates.

    Args:
        place_name: Name of the place (e.g., "Guntur", "Nagpur").

    Returns:
        Dict with 'lat', 'lon', 'name' if found, else None.
    """
    params = {
        "name": place_name,
        "count": 1,           # We only need the top result
        "language": "en",
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(GEOCODE_URL, params=params)
            data = response.json()

        # Check if we got results
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "lat": result["latitude"],
                "lon": result["longitude"],
                "name": result.get("name", place_name),
            }
        return None

    except Exception as e:
        print(f"[Geocode Error] {e}")
        return None


async def get_weather(lat: float, lon: float) -> dict | None:
    """
    Fetch 2-day weather forecast for given coordinates.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        Dict with weather summary, or None on failure.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 2,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            data = response.json()

        daily = data.get("daily", {})
        if not daily:
            return None

        # Build a simple summary for today and tomorrow
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_sum", [])
        wind = daily.get("windspeed_10m_max", [])

        summary_lines = []
        labels = ["Today", "Tomorrow"]

        for i in range(min(2, len(dates))):
            line = (
                f"{labels[i]} ({dates[i]}): "
                f"Max {max_temps[i]}°C, Min {min_temps[i]}°C, "
                f"Rain {rain[i]}mm, Wind {wind[i]}km/h"
            )
            summary_lines.append(line)

        return {
            "summary": "\n".join(summary_lines),
            "rain_tomorrow": rain[1] if len(rain) > 1 else 0,
        }

    except Exception as e:
        print(f"[Weather Error] {e}")
        return None


async def get_weather_for_place(place_name: str) -> str | None:
    """
    High-level function: place name → weather summary string.

    Args:
        place_name: Village/city name in India.

    Returns:
        Weather summary string, or None if location not found.
    """
    # Step 1: Convert place name to coordinates
    location = await geocode_location(place_name)
    if not location:
        return None

    # Step 2: Fetch weather for those coordinates
    weather = await get_weather(location["lat"], location["lon"])
    if not weather:
        return None

    return f"Location: {location['name']}\n{weather['summary']}"
