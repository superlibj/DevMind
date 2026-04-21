"""
Enhanced Weather tool for getting weather information and forecasts.

Provides current weather, forecasts, and weather-related information.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from datetime import datetime

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class WeatherTool(ACPTool):
    """Enhanced Weather tool for weather information and forecasts."""

    # Common city coordinates to avoid geocoding API calls
    CITY_COORDINATES = {
        "tokyo": (35.6762, 139.6503),
        "london": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "paris": (48.8566, 2.3522),
        "berlin": (52.5200, 13.4050),
        "sydney": (-33.8688, 151.2093),
        "beijing": (39.9042, 116.4074),
        "shanghai": (31.2304, 121.4737),
        "moscow": (55.7558, 37.6176),
        "dubai": (25.2048, 55.2708),
        "singapore": (1.3521, 103.8198),
        "hong kong": (22.3193, 114.1694),
        "mumbai": (19.0760, 72.8777),
        "delhi": (28.7041, 77.1025),
        "seoul": (37.5665, 126.9780),
        "los angeles": (34.0522, -118.2437),
        "chicago": (41.8781, -87.6298),
        "toronto": (43.6532, -79.3832),
        "vancouver": (49.2827, -123.1207),
        "mexico city": (19.4326, -99.1332),
        "sao paulo": (-23.5558, -46.6396),
        "buenos aires": (-34.6118, -58.3960),
        "cairo": (30.0444, 31.2357),
        "lagos": (6.5244, 3.3792),
        "cape town": (-33.9249, 18.4241),
        "wuxi": (31.5618, 120.2864),  # User's current city
    }

    def __init__(self):
        """Initialize Weather tool."""
        spec = ACPToolSpec(
            name="Weather",
            description="Gets weather information including current conditions, forecasts, and weather alerts",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name, address, or 'current' for current location"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude for weather lookup"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude for weather lookup"
                    },
                    "forecast_days": {
                        "type": "integer",
                        "description": "Number of forecast days (1-7)",
                        "minimum": 1,
                        "maximum": 7,
                        "default": 3
                    },
                    "include_hourly": {
                        "type": "boolean",
                        "description": "Include hourly forecast for today",
                        "default": False
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature units (metric=Celsius, imperial=Fahrenheit)",
                        "default": "metric"
                    }
                }
            },
            capabilities=["weather_services", "web_access", "data_retrieval"],
            security_level="standard",
            timeout_seconds=120
        )
        super().__init__(spec)

    def _extract_payload_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from payload, handling both direct and nested input formats."""
        # Handle nested input format: {"input": {"location": "..."}}
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"]
        # Handle direct format: {"location": "..."}
        return payload

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the weather request."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        # Check if we have location info
        has_location = bool(params.get("location", "").strip())
        has_coords = params.get("latitude") is not None and params.get("longitude") is not None

        if not has_location and not has_coords:
            # Default to current location if no parameters
            return None

        # Validate coordinates if provided
        if params.get("latitude") is not None:
            try:
                lat = float(params["latitude"])
                if lat < -90 or lat > 90:
                    return "latitude must be between -90 and 90"
            except (ValueError, TypeError):
                return "latitude must be a valid number"

        if params.get("longitude") is not None:
            try:
                lon = float(params["longitude"])
                if lon < -180 or lon > 180:
                    return "longitude must be between -180 and 180"
            except (ValueError, TypeError):
                return "longitude must be a valid number"

        # Validate forecast days
        forecast_days = params.get("forecast_days", 3)
        if forecast_days is not None:
            try:
                days = int(forecast_days)
                if days < 1 or days > 7:
                    return "forecast_days must be between 1 and 7"
            except (ValueError, TypeError):
                return "forecast_days must be a valid integer"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the weather lookup."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        location_name = params.get("location", "").strip()
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        forecast_days = params.get("forecast_days", 3)
        include_hourly = params.get("include_hourly", False)
        units = params.get("units", "metric")

        try:
            # Get coordinates if not provided
            if latitude is None or longitude is None:
                if location_name.lower() == "current" or not location_name:
                    # Get current location
                    coords = await self._get_current_location_coords()
                    if coords:
                        latitude, longitude = coords
                        # Use a simple location name to avoid extra API call
                        location_name = "Current Location"
                else:
                    # First try our coordinate cache for common cities
                    coords = self._get_city_coordinates(location_name)
                    if coords:
                        latitude, longitude = coords
                        logger.info(f"Using cached coordinates for '{location_name}'")
                    else:
                        # Try to geocode the location
                        coords = await self._geocode_location(location_name)
                        if coords:
                            latitude, longitude = coords
                        else:
                            # Geocoding failed, fall back to current location
                            logger.warning(f"Geocoding failed for '{location_name}', falling back to current location")
                            coords = await self._get_current_location_coords()
                            if coords:
                                latitude, longitude = coords
                                location_name = f"Current Location (requested: {location_name})"

                if latitude is None or longitude is None:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=(
                            f"Could not determine location coordinates. "
                            f"Unable to geocode '{location_name or 'specified location'}' "
                            f"and current location detection also failed. "
                            f"This may be due to network connectivity issues."
                        )
                    )

            # Get weather data
            weather_data = await self._get_weather_data(
                latitude, longitude, forecast_days, include_hourly, units
            )

            if weather_data:
                # Format the result - use simplified format for better LLM processing
                result_text = self._format_simple_weather_result(weather_data, location_name, units)

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=result_text,
                    metadata={
                        "location": location_name,
                        "coordinates": {"latitude": latitude, "longitude": longitude},
                        "units": units,
                        "forecast_days": forecast_days,
                        "current_temp": weather_data.get("current", {}).get("temperature"),
                        "condition": weather_data.get("current", {}).get("condition"),
                        "raw_data": weather_data  # Include raw data for debugging
                    }
                )
            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Could not retrieve weather data"
                )

        except Exception as e:
            logger.exception(f"Error in weather lookup")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error getting weather information: {str(e)}"
            )

    async def _get_current_location_coords(self) -> Optional[tuple]:
        """Get current location coordinates using IP geolocation."""
        # Try multiple services for better reliability and speed
        services = [
            "https://ipapi.co/json/",
            "http://ip-api.com/json/"
        ]

        for service_url in services:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(service_url, timeout=8) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Handle different response formats
                            if service_url.startswith("https://ipapi.co"):
                                if data.get("latitude") and data.get("longitude"):
                                    return (data["latitude"], data["longitude"])
                            elif service_url.startswith("http://ip-api.com"):
                                if data.get("lat") and data.get("lon") and data.get("status") == "success":
                                    return (data["lat"], data["lon"])

            except Exception as e:
                logger.warning(f"IP geolocation failed for {service_url}: {e}")
                continue

        logger.warning("All IP geolocation services failed")
        return None

    def _get_city_coordinates(self, city_name: str) -> Optional[tuple]:
        """Get coordinates for a city from our cache.

        Args:
            city_name: City name to look up

        Returns:
            Tuple of (latitude, longitude) if found, None otherwise
        """
        if not city_name:
            return None

        # Normalize city name for lookup
        normalized = city_name.lower().strip()

        # Remove common suffixes and prefixes
        normalized = normalized.replace(", china", "").replace(", japan", "").replace(", uk", "")
        normalized = normalized.replace(", usa", "").replace(", us", "").replace(", france", "")
        normalized = normalized.replace(", germany", "").replace(", australia", "")

        # Direct lookup
        if normalized in self.CITY_COORDINATES:
            return self.CITY_COORDINATES[normalized]

        # Try partial matches for compound city names
        for cached_city, coords in self.CITY_COORDINATES.items():
            if cached_city in normalized or normalized in cached_city:
                logger.info(f"Found partial match: '{normalized}' -> '{cached_city}'")
                return coords

        return None

    async def _geocode_location(self, location: str) -> Optional[tuple]:
        """Convert location name to coordinates."""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": location,
                "format": "json",
                "limit": 1
            }

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "DevMind-WeatherTool/1.0"}
                async with session.get(url, params=params, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            return (float(data[0]["lat"]), float(data[0]["lon"]))
        except Exception as e:
            logger.warning(f"Geocoding failed for '{location}': {e}")
        return None

    async def _get_location_name(self, latitude: float, longitude: float) -> str:
        """Get location name from coordinates."""
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "zoom": 10
            }

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "DevMind-WeatherTool/1.0"}
                async with session.get(url, params=params, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get("address"):
                            addr = data["address"]
                            city = addr.get("city") or addr.get("town") or addr.get("village")
                            country = addr.get("country")
                            if city and country:
                                return f"{city}, {country}"
        except Exception:
            pass
        return f"Location {latitude:.2f}, {longitude:.2f}"

    async def _get_weather_data(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int,
        include_hourly: bool,
        units: str
    ) -> Optional[Dict[str, Any]]:
        """Get weather data using Open-Meteo API (free, no API key required)."""
        try:
            # Open-Meteo API
            url = "https://api.open-meteo.com/v1/forecast"

            # Temperature unit
            temp_unit = "celsius" if units == "metric" else "fahrenheit"
            wind_unit = "kmh" if units == "metric" else "mph"

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature",
                           "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m"],
                "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min",
                         "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max"],
                "temperature_unit": temp_unit,
                "wind_speed_unit": wind_unit,
                "precipitation_unit": "mm",
                "forecast_days": forecast_days,
                "timezone": "auto"
            }

            if include_hourly:
                params["hourly"] = ["temperature_2m", "weather_code", "precipitation_probability"]

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weather_data(data, units)

        except Exception as e:
            logger.warning(f"Weather API request failed: {e}")
        return None

    def _parse_weather_data(self, data: Dict[str, Any], units: str) -> Dict[str, Any]:
        """Parse Open-Meteo weather data."""
        result = {}

        # Current weather
        if "current" in data:
            current = data["current"]
            result["current"] = {
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "wind_direction": current.get("wind_direction_10m"),
                "precipitation": current.get("precipitation"),
                "condition": self._get_weather_condition(current.get("weather_code")),
                "weather_code": current.get("weather_code")
            }

        # Daily forecast
        if "daily" in data:
            daily = data["daily"]
            result["daily"] = []

            for i in range(len(daily.get("time", []))):
                day_data = {
                    "date": daily["time"][i],
                    "temp_max": daily["temperature_2m_max"][i] if i < len(daily["temperature_2m_max"]) else None,
                    "temp_min": daily["temperature_2m_min"][i] if i < len(daily["temperature_2m_min"]) else None,
                    "precipitation": daily["precipitation_sum"][i] if i < len(daily["precipitation_sum"]) else None,
                    "precipitation_probability": daily["precipitation_probability_max"][i] if i < len(daily["precipitation_probability_max"]) else None,
                    "wind_speed": daily["wind_speed_10m_max"][i] if i < len(daily["wind_speed_10m_max"]) else None,
                    "condition": self._get_weather_condition(daily["weather_code"][i] if i < len(daily["weather_code"]) else None),
                    "weather_code": daily["weather_code"][i] if i < len(daily["weather_code"]) else None
                }
                result["daily"].append(day_data)

        # Hourly forecast (if requested)
        if "hourly" in data:
            hourly = data["hourly"]
            result["hourly"] = []

            # Only include next 12 hours
            for i in range(min(12, len(hourly.get("time", [])))):
                hour_data = {
                    "time": hourly["time"][i],
                    "temperature": hourly["temperature_2m"][i] if i < len(hourly["temperature_2m"]) else None,
                    "precipitation_probability": hourly["precipitation_probability"][i] if i < len(hourly["precipitation_probability"]) else None,
                    "condition": self._get_weather_condition(hourly["weather_code"][i] if i < len(hourly["weather_code"]) else None)
                }
                result["hourly"].append(hour_data)

        result["units"] = units
        return result

    def _get_weather_condition(self, weather_code: Optional[int]) -> str:
        """Convert WMO weather code to descriptive condition."""
        if weather_code is None:
            return "Unknown"

        # WMO weather interpretation codes
        conditions = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }

        return conditions.get(weather_code, f"Weather code {weather_code}")

    def _format_simple_weather_result(self, weather_data: Dict[str, Any], location: str, units: str) -> str:
        """Format weather data into a simple, LLM-friendly result."""
        result_lines = []

        temp_unit = "C" if units == "metric" else "F"
        speed_unit = "km/h" if units == "metric" else "mph"

        # Header
        result_lines.append(f"Weather for {location}:")
        result_lines.append("")

        # Current weather
        if "current" in weather_data:
            current = weather_data["current"]
            result_lines.append("Current conditions:")

            if current.get("temperature") is not None:
                temp_line = f"Temperature: {current['temperature']:.1f} {temp_unit}"
                if current.get("feels_like") is not None:
                    temp_line += f" (feels like {current['feels_like']:.1f} {temp_unit})"
                result_lines.append(temp_line)

            if current.get("condition"):
                result_lines.append(f"Condition: {current['condition']}")

            if current.get("humidity") is not None:
                result_lines.append(f"Humidity: {current['humidity']:.0f}%")
            if current.get("wind_speed") is not None:
                result_lines.append(f"Wind: {current['wind_speed']:.1f} {speed_unit}")

            result_lines.append("")

        # Daily forecast
        if "daily" in weather_data and weather_data["daily"]:
            result_lines.append("Forecast:")

            for i, day in enumerate(weather_data["daily"][:3]):  # Max 3 days to keep it simple
                date_str = day["date"]
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if i == 0:
                        day_name = "Today"
                    elif i == 1:
                        day_name = "Tomorrow"
                    elif i == 2:
                        day_name = "Day after tomorrow"
                    else:
                        day_name = date_obj.strftime("%A")
                except:
                    day_name = date_str

                temp_range = ""
                if day.get("temp_max") is not None and day.get("temp_min") is not None:
                    temp_range = f"{day['temp_min']:.0f} to {day['temp_max']:.0f} {temp_unit}"

                condition = day.get("condition", "")
                rain_prob = day.get("precipitation_probability")

                forecast_line = f"{day_name}: {temp_range}"
                if condition:
                    forecast_line += f", {condition}"
                if rain_prob and rain_prob > 20:
                    forecast_line += f" ({rain_prob:.0f}% chance of rain)"

                result_lines.append(forecast_line)

        return "\n".join(result_lines)

    def _format_weather_result(self, weather_data: Dict[str, Any], location: str, units: str) -> str:
        """Format weather data into a readable result."""
        result_lines = []

        temp_unit = "°C" if units == "metric" else "°F"
        speed_unit = "km/h" if units == "metric" else "mph"

        # Header
        result_lines.append(f"🌤️ **Weather for {location}**")
        result_lines.append("")

        # Current weather
        if "current" in weather_data:
            current = weather_data["current"]
            result_lines.append("📍 **Current Conditions**")

            if current.get("temperature") is not None:
                temp_line = f"🌡️ **Temperature**: {current['temperature']:.1f}{temp_unit}"
                if current.get("feels_like") is not None:
                    temp_line += f" (feels like {current['feels_like']:.1f}{temp_unit})"
                result_lines.append(temp_line)

            if current.get("condition"):
                result_lines.append(f"☁️ **Condition**: {current['condition']}")

            details = []
            if current.get("humidity") is not None:
                details.append(f"Humidity: {current['humidity']:.0f}%")
            if current.get("wind_speed") is not None:
                details.append(f"Wind: {current['wind_speed']:.1f} {speed_unit}")
            if current.get("precipitation") is not None and current["precipitation"] > 0:
                details.append(f"Precipitation: {current['precipitation']:.1f} mm")

            if details:
                result_lines.append(f"💨 **Details**: {' | '.join(details)}")

            result_lines.append("")

        # Daily forecast
        if "daily" in weather_data and weather_data["daily"]:
            result_lines.append("📅 **Forecast**")

            for i, day in enumerate(weather_data["daily"][:7]):  # Max 7 days
                date_str = day["date"]
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if i == 0:
                        day_name = "Today"
                    elif i == 1:
                        day_name = "Tomorrow"
                    else:
                        day_name = date_obj.strftime("%A")
                except:
                    day_name = date_str

                temp_range = ""
                if day.get("temp_max") is not None and day.get("temp_min") is not None:
                    temp_range = f"{day['temp_min']:.0f}° - {day['temp_max']:.0f}{temp_unit}"

                condition = day.get("condition", "")

                forecast_line = f"📆 **{day_name}**: {temp_range}"
                if condition:
                    forecast_line += f" | {condition}"

                if day.get("precipitation_probability") and day["precipitation_probability"] > 20:
                    forecast_line += f" | {day['precipitation_probability']:.0f}% chance of rain"

                result_lines.append(forecast_line)

        # Hourly forecast (if included)
        if "hourly" in weather_data and weather_data["hourly"]:
            result_lines.append("")
            result_lines.append("🕐 **Hourly Forecast (Next 12 Hours)**")

            for hour in weather_data["hourly"][:12]:
                try:
                    hour_time = datetime.fromisoformat(hour["time"].replace("Z", "+00:00"))
                    time_str = hour_time.strftime("%H:%M")
                except:
                    time_str = hour["time"][-5:]  # Extract time portion

                temp = hour.get("temperature")
                condition = hour.get("condition", "")
                precip_prob = hour.get("precipitation_probability")

                hourly_line = f"🕐 **{time_str}**: {temp:.0f}{temp_unit}"
                if condition:
                    hourly_line += f" | {condition}"
                if precip_prob and precip_prob > 20:
                    hourly_line += f" | {precip_prob:.0f}% rain"

                result_lines.append(hourly_line)

        return "\n".join(result_lines)

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        params = self._extract_payload_params(message.payload)
        location = params.get("location", "current location")
        self.logger.debug(f"Getting weather for: {location}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            location = result.metadata.get("location", "Unknown")
            temp = result.metadata.get("current_temp")
            condition = result.metadata.get("condition")
            self.logger.debug(f"Weather for {location}: {temp}° {condition}")


# Create singleton instance
weather_tool = WeatherTool()