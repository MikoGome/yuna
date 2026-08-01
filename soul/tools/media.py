import sys
import shutil
import subprocess

def manage_media(
    action: str = "play-pause", 
    player: str = "", 
    offset: int = 15, 
    timestamp: str = "",
    volume_level: int = 50,
    query: str = ""
) -> str:
    """
    Controls OS media playback: play, pause, seek, volume control, search/play on Spotify, skip tracks, stop media, or get metadata.
    
    Args:
        action (str): The playback command. Must be one of: 'play-pause', 'play', 'pause', 'next', 'previous', 'seek-forward', 'seek-backward', 'seek-absolute', 'stop', 'volume', 'search', or 'metadata'.
        player (str): Optional specific media player to target (e.g., 'spotify', 'mpv', 'firefox'). Defaults to active player.
        offset (int): Number of seconds to jump when using 'seek-forward' or 'seek-backward'. Defaults to 15 seconds.
        timestamp (str): The absolute timestamp to jump to when using 'seek-absolute' (e.g., '120', '2:00', or '1:15:30').
        volume_level (int): Target volume level from 0 to 100 when action is 'volume'. Defaults to 50.
        query (str): Search term for tracks/artists when action is 'search' (primarily supports Spotify/Linux playerctl).
    """
    action = action.lower().strip()
    player = player.lower().strip()
    
    valid_actions = {
        "play-pause", "play", "pause", "next", "previous", 
        "seek-forward", "seek-backward", "seek-absolute", "stop",
        "volume", "search", "metadata"
    }
    
    if action not in valid_actions:
        return f"Error: Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}."

    # Ensure offset is a positive integer for relative seeking
    try:
        offset = abs(int(offset))
    except (ValueError, TypeError):
        offset = 15

    # Ensure volume is bounded between 0 and 100
    try:
        volume_level = max(0, min(100, int(volume_level)))
    except (ValueError, TypeError):
        volume_level = 50

    # Helper: Convert "MM:SS" or "HH:MM:SS" strings to total seconds for absolute seeking
    def parse_timestamp_to_seconds(ts_str: str) -> int:
        ts_str = ts_str.strip()
        if not ts_str:
            return -1
        parts = ts_str.split(':')
        try:
            parts = [int(p) for p in parts]
            if len(parts) == 1:
                return parts[0]
            elif len(parts) == 2:
                return parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
        except ValueError:
            pass
        return -1

    # ==========================================
    # 1. LINUX SUPPORT (playerctl)
    # ==========================================
    if sys.platform.startswith('linux'):
        if not shutil.which('playerctl'):
            return "Error: 'playerctl' is not installed. Install via your package manager (e.g., sudo apt install playerctl)."
        
        cmd = ['playerctl']
        if player:
            cmd.extend(['--player', player])
            
        if action == "metadata":
            # Format output to clearly display playback status, artist, track, and album
            format_str = "{{ status }}: {{ artist }} - {{ title }} ({{ album }})"
            cmd.extend(["metadata", "--format", format_str])
            try:
                res = subprocess.run(cmd, check=True, capture_output=True, text=True)
                output = res.stdout.strip()
                return f"Current Media: {output}" if output else "No media metadata available."
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.strip() if e.stderr else "No active media player found."
                return f"Error fetching metadata: {err_msg}"

        elif action in ("seek-forward", "seek-backward"):
            direction = "+" if action == "seek-forward" else "-"
            cmd.extend(["position", f"{offset}{direction}"])
            action_desc = f"seeked {action.split('-')[1]} by {offset}s"
        elif action == "seek-absolute":
            target_seconds = parse_timestamp_to_seconds(timestamp)
            if target_seconds < 0:
                return f"Error: Invalid timestamp format '{timestamp}'. Use seconds ('120') or MM:SS ('2:00')."
            cmd.extend(["position", str(target_seconds)])
            action_desc = f"jumped to timestamp {timestamp} ({target_seconds}s)"
        elif action == "volume":
            vol_float = volume_level / 100.0
            cmd.extend(["volume", str(vol_float)])
            action_desc = f"set volume to {volume_level}%"
        elif action == "search":
            if not query.strip():
                return "Error: A search query must be provided when using action 'search'."
            spotify_search_uri = f"spotify:search:{query.replace(' ', '%20')}"
            cmd.extend(["open", spotify_search_uri])
            action_desc = f"searched and played '{query}'"
        else:
            cmd.append(action)
            action_desc = f"sent '{action}' command"

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            target_str = f"on '{player}'" if player else "on default media player"
            return f"Successfully {action_desc} {target_str}."
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() if e.stderr else "No active media player found."
            return f"Error controlling media: {err_msg}"

    # ==========================================
    # 2. macOS SUPPORT (AppleScript / Music App)
    # ==========================================
    elif sys.platform == 'darwin':
        try:
            target_app = player if player else "Music"
            if action == "metadata":
                script = f'''
                tell application "System Events"
                    if not (exists process "{target_app}") then return "Player not running"
                end tell
                tell application "{target_app}"
                    set trackName to name of current track
                    set trackArtist to artist of current track
                    set trackAlbum to album of current track
                    set playerState to player state as string
                    return playerState & ": " & trackArtist & " - " & trackName & " (" & trackAlbum & ")"
                end tell
                '''
                res = subprocess.run(['osascript', '-e', script], check=True, capture_output=True, text=True)
                output = res.stdout.strip()
                return f"Current Media ({target_app}): {output}"
            elif action in ("seek-forward", "seek-backward"):
                sign = "+" if action == "seek-forward" else "-"
                script = (
                    f'tell application "{target_app}" to set player position to '
                    f'(player position {sign} {offset})'
                )
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return f"Successfully seeked {offset} seconds on macOS ({target_app})."
            elif action == "seek-absolute":
                target_seconds = parse_timestamp_to_seconds(timestamp)
                if target_seconds < 0:
                    return f"Error: Invalid timestamp format '{timestamp}'."
                script = f'tell application "{target_app}" to set player position to {target_seconds}'
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return f"Successfully jumped to {timestamp} on macOS ({target_app})."
            elif action == "volume":
                script = f'tell application "{target_app}" to set sound volume to {volume_level}'
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return f"Successfully set {target_app} volume to {volume_level}%."
            elif action == "search":
                if not query.strip():
                    return "Error: A search query must be provided."
                script = f'tell application "Finder" to open location "spotify:search:{query}"'
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return f"Successfully searched Spotify for '{query}' on macOS."
            else:
                osx_actions = {
                    "play-pause": "key code 100",
                    "play": "key code 100",
                    "pause": "key code 100",
                    "next": "key code 101",
                    "previous": "key code 98",
                    "stop": "key code 100"
                }
                script = f'tell application "System Events" to {osx_actions[action]}'
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return f"Successfully sent '{action}' media command via AppleScript."
        except Exception as e:
            return f"Error controlling media on macOS: {str(e)}"

    # ==========================================
    # 3. WINDOWS SUPPORT (PowerShell / WinRT)
    # ==========================================
    elif sys.platform == 'win32':
        if action == "metadata":
            # Using WinRT GlobalSystemMediaTransportControlsSessionManager to get current media metadata
            ps_script = """
            $null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime]
            $async = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
            $manager = $async.GetResults()
            $session = $manager.GetCurrentSession()
            if ($null -eq $session) {
                Write-Output "No active media session."
            } else {
                $mediaAsync = $session.TryGetMediaPropertiesAsync()
                $mediaProps = $mediaAsync.GetResults()
                $artist = $mediaProps.Artist
                $title = $mediaProps.Title
                $album = $mediaProps.AlbumTitle
                Write-Output "$artist - $title ($album)"
            }
            """
            try:
                res = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_script], 
                    check=True, capture_output=True, text=True
                )
                output = res.stdout.strip()
                return f"Current Media: {output}" if output else "No media metadata available."
            except Exception as e:
                return f"Error fetching metadata on Windows: {str(e)}"

        if action in ("seek-forward", "seek-backward", "seek-absolute"):
            return "Error: Time seeking/timestamps are not globally supported via Windows system keys. Use Linux/playerctl for seeking."
        
        if action == "volume":
            return "Error: Exact volume percentages via global keys are restricted on Windows. Use media keys or a specialized library."
            
        if action == "search":
            if not query.strip():
                return "Error: A search query must be provided."
            ps_script = f"Start-Process 'spotify:search:{query}'"
            try:
                subprocess.run(['powershell', '-Command', ps_script], check=True, capture_output=True)
                return f"Successfully searched Spotify for '{query}' on Windows."
            except Exception as e:
                return f"Error opening Spotify search on Windows: {str(e)}"
            
        win_keys = {
            "play-pause": "{MEDIA_PLAY_PAUSE}",
            "play": "{MEDIA_PLAY_PAUSE}",
            "pause": "{MEDIA_PLAY_PAUSE}",
            "next": "{MEDIA_NEXT_TRACK}",
            "previous": "{MEDIA_PREV_TRACK}",
            "stop": "{MEDIA_STOP}"
        }
        key = win_keys[action]
        ps_script = f"$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys('{key}')"
        try:
            subprocess.run(['powershell', '-Command', ps_script], check=True, capture_output=True)
            return f"Successfully sent '{action}' media command via PowerShell."
        except Exception as e:
            return f"Error controlling media on Windows: {str(e)}"

    return "Error: Unsupported operating system for media control."

# ==========================================
# UPDATED TOOL METADATA DEFINITION FOR OLLAMA
# ==========================================
media_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'manage_media',
            'description': 'Control OS media playback: play/pause, skip tracks, stop media, fast-forward/rewind, jump to timestamps, control volume, search Spotify, or get current track metadata.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'action': {
                        'type': 'string',
                        'enum': [
                            'play-pause', 'play', 'pause', 'next', 'previous',
                            'seek-forward', 'seek-backward', 'seek-absolute', 'stop',
                            'volume', 'search', 'metadata'
                        ],
                        'description': 'The media command to send. Use "metadata" to check the currently playing artist, track, and album.',
                    },
                    'player': {
                        'type': 'string',
                        'description': 'Optional name of a specific application to target (e.g., "spotify", "mpv", "firefox").',
                    },
                    'offset': {
                        'type': 'integer',
                        'description': 'Number of seconds to jump when using seek-forward or seek-backward. Defaults to 15.',
                    },
                    'timestamp': {
                        'type': 'string',
                        'description': 'Timestamp to jump to when using "seek-absolute" (e.g., "120" for seconds, "2:00" for 2 minutes, or "1:00:00" for 1 hour).',
                    },
                    'volume_level': {
                        'type': 'integer',
                        'description': 'Target volume percentage from 0 to 100 when action is set to "volume". Defaults to 50.',
                    },
                    'query': {
                        'type': 'string',
                        'description': 'The search term (artist, track, album) to query when action is set to "search".',
                    },
                },
                'required': ['action'],
            },
        },
    }
]