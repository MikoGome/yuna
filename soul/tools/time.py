import datetime
import zoneinfo

def get_current_time(time_format: str = "%Y-%m-%d %I:%M %p %Z", timezone_str: str = None, *args, **kwargs) -> dict:
    """
    Retrieves the current time, optionally for a specific timezone.
    Returns a dictionary with 'success' (boolean) and 'message' (string).
    """
    try:
        # =====================================================================
        # 1. Fetching Timezone-Aware Time
        # =====================================================================
        
        if timezone_str:
            # Get time for a specific timezone (e.g., "Asia/Tokyo")
            tz = zoneinfo.ZoneInfo(timezone_str)
            current_time = datetime.datetime.now(tz)
        else:
            # Fallback to the system's local timezone
            current_time = datetime.datetime.now().astimezone()
        
        # Format the time
        formatted_time = current_time.strftime(time_format).strip()
        
        return {"success": True, "message": formatted_time}

    except zoneinfo.ZoneInfoNotFoundError:
        return {"success": False, "message": f"Timezone '{timezone_str}' not found. Please use standard IANA timezones (e.g., 'Europe/London')."}
    except Exception as e:
        return {"success": False, "message": f"Failed to retrieve the current time. Error: {str(e)}"}


# =====================================================================
# 2. Ollama Tool Definition Metadata
# =====================================================================
time_tool_meta = [{
    'type': 'function',
    'function': {
        'name': 'get_current_time',
        'description': 'Retrieves the current time and date, optionally for a specific timezone.',
        'parameters': {
            'type': 'object',
            'properties': {
                'timezone_str': {
                    'type': 'string',
                    'description': 'Optional. The IANA timezone name to check the time for (e.g., "America/Los_Angeles", "Europe/London", "Asia/Tokyo"). If omitted, returns local system time.',
                },
                'time_format': {
                    'type': 'string',
                    'description': 'Optional. The strftime format string. Defaults to "%Y-%m-%d %I:%M %p %Z" (e.g., 2023-10-25 02:30 PM PDT).',
                }
            },
            'required': [],
        },
    },
}]