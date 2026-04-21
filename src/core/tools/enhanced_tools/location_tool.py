"""
Enhanced Location tool for getting geographical location information.

Provides location detection and geographic information lookup capabilities.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
import aiohttp

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class LocationTool(ACPTool):
    """Enhanced Location tool for geographic information."""

    def __init__(self):
        """Initialize Location tool."""
        spec = ACPToolSpec(
            name="Location",
            description="Gets location information including current location, coordinates, and location details",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Location query (city, address, or 'current' for auto-detect)"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude for reverse geocoding"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude for reverse geocoding"
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed location information",
                        "default": True
                    }
                }
            },
            capabilities=["location_services", "web_access", "geolocation"],
            security_level="standard",
            timeout_seconds=60
        )
        super().__init__(spec)

    def _extract_payload_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from payload, handling both direct and nested input formats."""
        # Handle nested input format: {"input": {"query": "..."}}
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"]
        # Handle direct format: {"query": "..."}
        return payload

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the location request."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        # At least one of query or coordinates should be provided
        has_query = bool(params.get("query", "").strip())
        has_coords = params.get("latitude") is not None and params.get("longitude") is not None

        if not has_query and not has_coords:
            # If no parameters provided, default to current location detection
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

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the location lookup."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        query = params.get("query", "").strip().lower()
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        include_details = params.get("include_details", True)

        try:
            # Determine the type of location request
            if latitude is not None and longitude is not None:
                # Reverse geocoding
                result_data = await self._reverse_geocode(float(latitude), float(longitude), include_details)
            elif query == "current" or not query:
                # Auto-detect current location
                result_data = await self._get_current_location(include_details)
            else:
                # Forward geocoding (search by location name)
                result_data = await self._geocode_location(query, include_details)

            if result_data:
                # Format the result
                result_text = self._format_location_result(result_data)

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=result_text,
                    metadata={
                        "query": query,
                        "coordinates": {
                            "latitude": result_data.get("latitude"),
                            "longitude": result_data.get("longitude")
                        },
                        "location": result_data.get("display_name"),
                        "country": result_data.get("country"),
                        "city": result_data.get("city")
                    }
                )
            else:
                # Provide helpful error messages based on the request type
                if query == "current" or not query:
                    error_msg = (
                        "Unable to detect your current location automatically. "
                        "This may be due to network connectivity issues or firewall restrictions. "
                        "You can try specifying a city name instead, like 'Tokyo' or 'New York'."
                    )
                else:
                    error_msg = (
                        f"Could not find location information for '{query}'. "
                        "Please check the spelling or try a different location name."
                    )

                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=error_msg
                )

        except Exception as e:
            logger.exception(f"Error in location lookup")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error getting location information: {str(e)}"
            )

    async def _get_current_location(self, include_details: bool = True) -> Optional[Dict[str, Any]]:
        """Get current location using IP geolocation."""
        # Try multiple IP geolocation services for better reliability
        services = [
            ("https://ipapi.co/json/", self._parse_ipapi_response),
            ("http://ip-api.com/json/", self._parse_ipapi_com_response),
            ("https://httpbin.org/ip", self._parse_httpbin_response)
        ]

        for service_url, parser in services:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(service_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            result = parser(data, include_details)
                            if result and result.get("latitude") and result.get("longitude"):
                                logger.info(f"IP geolocation successful via {service_url}")
                                return result

            except Exception as e:
                logger.warning(f"IP geolocation failed for {service_url}: {e}")
                continue

        # All services failed, return None to indicate failure
        logger.error("All IP geolocation services failed")
        return None

    def _parse_ipapi_response(self, data: Dict, include_details: bool) -> Optional[Dict[str, Any]]:
        """Parse ipapi.co response."""
        if data.get("latitude") and data.get("longitude"):
            result = {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "display_name": f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}",
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "country_code": data.get("country_code"),
                "postal": data.get("postal"),
                "timezone": data.get("timezone"),
                "source": "ipapi.co"
            }

            if include_details:
                result.update({
                    "ip": data.get("ip"),
                    "org": data.get("org"),
                    "asn": data.get("asn")
                })

            return result
        return None

    def _parse_ipapi_com_response(self, data: Dict, include_details: bool) -> Optional[Dict[str, Any]]:
        """Parse ip-api.com response."""
        if data.get("lat") and data.get("lon") and data.get("status") == "success":
            result = {
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "display_name": f"{data.get('city', 'Unknown')}, {data.get('country', 'Unknown')}",
                "city": data.get("city"),
                "region": data.get("regionName"),
                "country": data.get("country"),
                "country_code": data.get("countryCode"),
                "postal": data.get("zip"),
                "timezone": data.get("timezone"),
                "source": "ip-api.com"
            }

            if include_details:
                result.update({
                    "ip": data.get("query"),
                    "org": data.get("org"),
                    "isp": data.get("isp")
                })

            return result
        return None

    def _parse_httpbin_response(self, data: Dict, include_details: bool) -> Optional[Dict[str, Any]]:
        """Parse httpbin response (IP only, no location data)."""
        # This service only provides IP, so we can't get location
        return None

    async def _geocode_location(self, query: str, include_details: bool = True) -> Optional[Dict[str, Any]]:
        """Forward geocoding - convert location name to coordinates."""
        try:
            # Use Nominatim (OpenStreetMap) for geocoding (free)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1 if include_details else 0
            }

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "DevMind-LocationTool/1.0"}
                async with session.get(url, params=params, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data and len(data) > 0:
                            location = data[0]

                            result = {
                                "latitude": float(location["lat"]),
                                "longitude": float(location["lon"]),
                                "display_name": location["display_name"],
                                "source": "Nominatim geocoding"
                            }

                            if include_details and "address" in location:
                                addr = location["address"]
                                result.update({
                                    "city": addr.get("city") or addr.get("town") or addr.get("village"),
                                    "region": addr.get("state") or addr.get("province"),
                                    "country": addr.get("country"),
                                    "country_code": addr.get("country_code"),
                                    "postal": addr.get("postcode")
                                })

                            return result

        except Exception as e:
            logger.warning(f"Geocoding failed for '{query}': {e}")

        return None

    async def _reverse_geocode(self, latitude: float, longitude: float, include_details: bool = True) -> Optional[Dict[str, Any]]:
        """Reverse geocoding - convert coordinates to location name."""
        try:
            # Use Nominatim for reverse geocoding
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "addressdetails": 1 if include_details else 0
            }

            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "DevMind-LocationTool/1.0"}
                async with session.get(url, params=params, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data:
                            result = {
                                "latitude": latitude,
                                "longitude": longitude,
                                "display_name": data["display_name"],
                                "source": "Nominatim reverse geocoding"
                            }

                            if include_details and "address" in data:
                                addr = data["address"]
                                result.update({
                                    "city": addr.get("city") or addr.get("town") or addr.get("village"),
                                    "region": addr.get("state") or addr.get("province"),
                                    "country": addr.get("country"),
                                    "country_code": addr.get("country_code"),
                                    "postal": addr.get("postcode")
                                })

                            return result

        except Exception as e:
            logger.warning(f"Reverse geocoding failed for {latitude}, {longitude}: {e}")

        return None

    def _format_location_result(self, data: Dict[str, Any]) -> str:
        """Format location data into a readable result."""
        result_lines = []

        # Main location info
        if data.get("display_name"):
            result_lines.append(f"📍 **Location**: {data['display_name']}")

        # Coordinates
        if data.get("latitude") is not None and data.get("longitude") is not None:
            result_lines.append(f"🌐 **Coordinates**: {data['latitude']:.6f}, {data['longitude']:.6f}")

        # Detailed breakdown
        details = []
        if data.get("city"):
            details.append(f"City: {data['city']}")
        if data.get("region"):
            details.append(f"Region: {data['region']}")
        if data.get("country"):
            details.append(f"Country: {data['country']}")
        if data.get("postal"):
            details.append(f"Postal: {data['postal']}")

        if details:
            result_lines.append("📋 **Details**: " + " | ".join(details))

        # Additional info
        if data.get("timezone"):
            result_lines.append(f"🕐 **Timezone**: {data['timezone']}")

        if data.get("source"):
            result_lines.append(f"ℹ️ **Source**: {data['source']}")

        return "\n".join(result_lines)

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        params = self._extract_payload_params(message.payload)
        query = params.get("query", "current location")
        self.logger.debug(f"Looking up location: {query}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            location = result.metadata.get("location", "Unknown")
            self.logger.debug(f"Successfully found location: {location}")


# Create singleton instance
location_tool = LocationTool()