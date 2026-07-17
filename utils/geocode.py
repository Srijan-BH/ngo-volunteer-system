import requests
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def geocode_address(address_string: str) -> Optional[Tuple[float, float]]:
    """
    Uses the free Nominatim OpenStreetMap API to convert an address string into (longitude, latitude).
    Returns (lng, lat) or None if not found or on error.
    """
    if not address_string or not address_string.strip():
        return None

    try:
        # Nominatim requires a user-agent
        headers = {
            "User-Agent": "NGO-Volunteer-System/1.0 (contact@ngovolunteer.org)"
        }
        
        # We limit to 1 result
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address_string,
            "format": "json",
            "limit": 1
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            return (lng, lat)  # Note: MongoDB expects [longitude, latitude]
            
    except Exception as e:
        logger.error(f"Geocoding failed for address '{address_string}': {e}")
        
    return None
