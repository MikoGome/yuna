import os
import sys
import subprocess

def launch_steam_game(app_id: str, *args, **kwargs) -> dict:
    """
    Launches a Steam game using its Application ID (AppID) via the Steam URI protocol.
    Returns a dictionary with 'success' (boolean) and 'message' (string).
    """
    app_id = str(app_id).strip()
    platform = sys.platform
    steam_uri = f"steam://run/{app_id}"

    try:
        # =====================================================================
        # 1. OS-Specific URI Launching
        # =====================================================================
        
        if platform == 'darwin':
            # macOS uses 'open' to handle custom URI schemes
            cmd = ['open', steam_uri]
            result = subprocess.run(
                cmd, 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Attempted to launch Steam AppID '{app_id}' via macOS 'open'."}
            else:
                return {"success": False, "message": f"macOS failed to launch Steam game. {result.stderr.strip()}"}

        elif platform == 'win32':
            # Windows uses os.startfile natively for URI schemes
            try:
                os.startfile(steam_uri)
                return {"success": True, "message": f"Attempted to launch Steam AppID '{app_id}' via Windows os.startfile."}
            except Exception as e:
                # Fallback to shell start if os.startfile fails
                cmd_str = f'start "" "{steam_uri}"'
                result = subprocess.run(
                    cmd_str, 
                    shell=True, capture_output=True, text=True
                )
                if result.returncode == 0:
                    return {"success": True, "message": f"Attempted to launch Steam AppID '{app_id}' via Windows shell."}
                else:
                    return {"success": False, "message": f"Windows failed to launch Steam game. Error: {str(e)}"}

        elif platform.startswith('linux'):
            # Linux uses xdg-open to handle custom URI schemes
            cmd = ['xdg-open', steam_uri]
            result = subprocess.run(
                cmd, 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Attempted to launch Steam AppID '{app_id}' via xdg-open."}
            else:
                return {"success": False, "message": f"Linux failed to launch Steam game. {result.stderr.strip()}"}
            
        else:
            return {"success": False, "message": f"Unsupported operating system: {platform}"}

    except Exception as e:
        return {"success": False, "message": f"Failed to launch Steam game (AppID: {app_id}). Error: {str(e)}"}


# =====================================================================
# 2. Ollama Tool Definition Metadata
# =====================================================================
steam_tool_meta = [{
    'type': 'function',
    'function': {
        'name': 'launch_steam_game',
        'description': 'Launches a Steam game on the user\'s computer using its unique Steam Application ID (AppID).',
        'parameters': {
            'type': 'object',
            'properties': {
                'app_id': {
                    'type': 'string',
                    'description': 'The exact Steam Application ID (AppID) of the game to launch (e.g., "570" for Dota 2, "730" for CS:GO).',
                }
            },
            'required': ['app_id'],
        },
    },
}]