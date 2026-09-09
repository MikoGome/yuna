import urllib.parse
import webbrowser

from .browser import open_browser

def open_google_maps_directions(
    destination: str, 
    origin: str = None, 
    travel_mode: str = "driving", 
    incognito: bool = False
) -> str:
    """
    Opens Google Maps directions in the web browser to a specified destination.
    
    Args:
        destination (str): The target address, landmark, or coordinates (e.g., 'Eiffel Tower' or '100 Main St, New York, NY').
        origin (str, optional): The starting address or landmark. If omitted, Google Maps defaults to current location.
        travel_mode (str): The mode of transport: 'driving', 'walking', 'bicycling', or 'transit'.
        incognito (bool): Whether to open in incognito/private mode using the open_browser utility.
    """
    base_url = "https://www.google.com/maps/dir/?api=1"
    
    # Validate and normalize travel mode
    valid_modes = {"driving", "walking", "bicycling", "transit"}
    mode = travel_mode.lower().strip()
    if mode not in valid_modes:
        mode = "driving"

    # Build query parameters
    params = {
        "destination": destination.strip(),
        "travelmode": mode
    }
    
    if origin and origin.strip():
        params["origin"] = origin.strip()

    # Encode parameters cleanly into the URL
    full_url = f"{base_url}&{urllib.parse.urlencode(params)}"

    # Reuse the shared browser tool so incognito mode actually works
    open_browser(full_url, incognito=incognito)
    return f"Successfully opened Google Maps directions to '{destination}' ({mode} mode)"

google_maps_tools_meta = [
    {
        "type": "function",
        "function": {
            "name": "open_google_maps_directions",
            "description": "Open Google Maps in the browser with directions to a destination. Can specify an optional starting point and travel mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The target address, city, business name, or landmark to navigate to (e.g., 'LAX Airport' or '350 5th Ave, New York').",
                    },
                    "origin": {
                        "type": "string",
                        "description": "The starting location. Leave empty or null to use the user's current GPS location.",
                    },
                    "travel_mode": {
                        "type": "string",
                        "enum": ["driving", "walking", "bicycling", "transit"],
                        "description": "The transportation method for the route. Defaults to 'driving'.",
                    },
                    "incognito": {
                        "type": "boolean",
                        "description": "Set to true to open the map in an incognito/private browser window.",
                    },
                },
                "required": ["destination"],
            },
        },
    }
]