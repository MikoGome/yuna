import shutil
import subprocess
import difflib

def _get_monitors_info() -> list:
    """
    Parses `xrandr --listmonitors` to return a list of connected monitors
    ordered by index (0, 1, 2...) with their exact x_offset, y_offset, width, and height.
    """
    monitors = []
    try:
        proc = subprocess.run(
            ['xrandr', '--listmonitors'],
            capture_output=True,
            text=True,
            check=True
        )
        for line in proc.stdout.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 3:
                geom_str = parts[2]
                res_part, x_off, y_off = geom_str.split('+')
                w_str, h_str = res_part.split('x')
                width = int(w_str.split('/')[0])
                height = int(h_str.split('/')[0])
                
                monitors.append({
                    "x_offset": int(x_off),
                    "y_offset": int(y_off),
                    "width": width,
                    "height": height
                })
    except Exception:
        monitors.append({"x_offset": 0, "y_offset": 0, "width": 1920, "height": 1080})
    
    return monitors

def manage_window(
    window_name: str, 
    action: str = "move", 
    monitor: int = 0, 
    dx: int = 0,
    dy: int = 0
) -> str:
    """
    Manages an open Linux window using wmctrl and xdotool: move to monitor, maximize, minimize, restore, nudge, or close.
    
    Args:
        window_name (str): The case-insensitive WM_CLASS or title of the window (e.g., 'spotify', 'firefox', 'discord').
        action (str): Must be one of: 'move', 'maximize', 'minimize', 'restore', 'nudge', or 'close'.
        monitor (int): Target monitor index if action is 'move' (0 for primary, 1 for second monitor, etc.).
        dx (int): Horizontal nudge offset in pixels (positive for right, negative for left). Used when action is 'nudge'.
        dy (int): Vertical nudge offset in pixels (positive for down, negative for up). Used when action is 'nudge'.
    """
    window_name = window_name.strip()
    action = action.lower().strip()
    valid_actions = {"move", "maximize", "minimize", "restore", "nudge", "close"}
    
    if action not in valid_actions:
        return f"Error: Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}."

    if not shutil.which('wmctrl'):
        return "Error: 'wmctrl' is not installed. Please install it via your package manager."

    try:
        # 1. Get all currently open windows with geometry and WM_CLASS (-G adds geometry, -x adds WM_CLASS column)
        list_proc = subprocess.run(
            ['wmctrl', '-l', '-x', '-G'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        all_lines = list_proc.stdout.splitlines()
        
        parsed_windows = []
        for line in all_lines:
            # Format with -l -x -G: ID DESKTOP X Y WIDTH HEIGHT WM_CLASS MACHINE TITLE...
            parts = line.split(maxsplit=8)
            if len(parts) >= 8:
                title = parts[8] if len(parts) == 9 else ""
                parsed_windows.append({
                    "id": parts[0],
                    "x": int(parts[2]),
                    "y": int(parts[3]),
                    "width": int(parts[4]),
                    "height": int(parts[5]),
                    "wm_class": parts[6],
                    "title": title
                })
        
        if not parsed_windows:
            return "No open windows detected on the system."

        # 2. Match by WM_CLASS first (immune to title changes like Spotify song updates), then by Title
        best_match_obj = None
        for win in parsed_windows:
            if window_name.lower() in win["wm_class"].lower():
                best_match_obj = win
                break
        
        if not best_match_obj:
            for win in parsed_windows:
                if window_name.lower() in win["title"].lower():
                    best_match_obj = win
                    break
        
        # 3. Fuzzy matching fallback for typos against both class names and titles
        if not best_match_obj:
            candidates = [f"{w['wm_class']} | {w['title']}" for w in parsed_windows]
            matches = difflib.get_close_matches(window_name, candidates, n=1, cutoff=0.35)
            if matches:
                matched_str = matches[0]
                best_match_obj = next(w for w in parsed_windows if f"{w['wm_class']} | {w['title']}" == matched_str)
            else:
                available_apps = list(set(w["wm_class"].split('.')[-1] for w in parsed_windows if w["wm_class"]))
                return f"No open window found matching or similar to: '{window_name}'. Open apps: {', '.join(available_apps)}"

        # Use clean class name or title for user reporting
        best_match_name = best_match_obj["title"] or best_match_obj["wm_class"]
        win_id = best_match_obj["id"]

        # 4. Handle requested action
        if action == "maximize":
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,hidden'], capture_output=True)
            subprocess.run(
                ['wmctrl', '-i', '-r', win_id, '-b', 'add,maximized_vert,maximized_horz'],
                check=True,
                capture_output=True
            )
            return f"Successfully maximized '{best_match_name}'."

        elif action == "minimize":
            # Try xdotool first; fallback to wmctrl hidden state if xdotool is not installed
            if shutil.which('xdotool'):
                subprocess.run(
                    ['xdotool', 'windowminimize', win_id],
                    check=True,
                    capture_output=True
                )
                return f"Successfully minimized '{best_match_name}'."
            else:
                # EWMH fallback: adding the 'hidden' property minimizes/iconifies in most Linux window managers
                subprocess.run(
                    ['wmctrl', '-i', '-r', win_id, '-b', 'add,hidden'],
                    check=True,
                    capture_output=True
                )
                return f"Successfully minimized '{best_match_name}' (using wmctrl)."

        elif action == "restore":
            if shutil.which('xdotool'):
                subprocess.run(
                    ['xdotool', 'windowactivate', win_id],
                    capture_output=True
                )
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,hidden'], capture_output=True)
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,maximized_vert,maximized_horz'], capture_output=True)
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,fullscreen'], capture_output=True)
            return f"Successfully restored '{best_match_name}' to normal size and visibility."

        elif action == "close":
            subprocess.run(
                ['wmctrl', '-i', '-c', win_id],
                check=True,
                capture_output=True
            )
            return f"Successfully sent graceful close signal to '{best_match_name}'."

        elif action == "move":
            monitors = _get_monitors_info()
            
            if monitor >= len(monitors) or monitor < 0:
                monitor = 0
            
            target_monitor = monitors[monitor]
            
            target_x = target_monitor["x_offset"] + 50
            target_y = max(100, target_monitor["y_offset"] + (target_monitor["height"] - best_match_obj["height"]) // 4)

            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,hidden'], capture_output=True)
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,maximized_vert,maximized_horz'], capture_output=True)
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,fullscreen'], capture_output=True)
            
            subprocess.run(
                ['wmctrl', '-i', '-r', win_id, '-e', f'0,{target_x},{target_y},-1,-1'],
                check=True,
                capture_output=True
            )
            return f"Successfully moved '{best_match_name}' to Monitor {monitor} ({target_monitor['width']}x{target_monitor['height']} at X={target_x}, Y={target_y})."

        elif action == "nudge":
            if dx == 0 and dy == 0:
                return "Error: Please specify a non-zero dx (left/right) or dy (up/down) pixel offset to nudge."

            new_x = best_match_obj["x"] + dx
            new_y = best_match_obj["y"] + dy

            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,maximized_vert,maximized_horz'], capture_output=True)
            subprocess.run(['wmctrl', '-i', '-r', win_id, '-b', 'remove,fullscreen'], capture_output=True)

            subprocess.run(
                ['wmctrl', '-i', '-r', win_id, '-e', f'0,{new_x},{new_y},-1,-1'],
                check=True,
                capture_output=True
            )
            return f"Successfully nudged '{best_match_name}' by (dx={dx}px, dy={dy}px) to new position ({new_x}, {new_y})."

    except Exception as e:
        return f"An unexpected error occurred while trying to {action} '{window_name}': {str(e)}"


# Updated Tool Definition for Ollama (Explicit definitions for LLMs)
window_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'manage_window',
            'description': 'Manage an application window on Linux. Use this tool when the user wants to minimize, hide, maximize, restore, move, nudge, or close any application window (e.g., Spotify, Chrome, Terminal, Discord). Matches against stable application class names (WM_CLASS) as well as window titles.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'window_name': {
                        'type': 'string',
                        'description': 'The application class name (WM_CLASS) or window title to modify (e.g., "spotify", "firefox", "discord", "Terminal"). Case-insensitive.',
                    },
                    'action': {
                        'type': 'string',
                        'enum': ['move', 'maximize', 'minimize', 'restore', 'nudge', 'close'],
                        'description': 'The specific action to perform on the window. Must be one of: "minimize" (hide, iconify, or put away to taskbar/dock), "maximize" (make full screen/enlarge), "restore" (un-minimize or un-maximize back to normal), "move" (send to another monitor), "nudge" (adjust X/Y position by pixels), or "close" (gracefully quit/close the app).',
                    },
                    'monitor': {
                        'type': 'integer',
                        'description': 'The zero-indexed target monitor number (0 for primary, 1 for second monitor). Only used when action is "move".',
                    },
                    'dx': {
                        'type': 'integer',
                        'description': 'Horizontal nudge distance in pixels. Positive values move right, negative values move left. Only used when action is "nudge".',
                    },
                    'dy': {
                        'type': 'integer',
                        'description': 'Vertical nudge distance in pixels. Positive values move down, negative values move up. Only used when action is "nudge".',
                    },
                },
                'required': ['window_name', 'action'],
            },
        },
    }
]