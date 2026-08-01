import sys
import shutil
import subprocess
import pyperclip

def manage_clipboard(action: str = "read", text: str = "") -> str:
    """
    Reads from or writes to the system clipboard.
    
    Args:
        action (str): The clipboard operation to perform. Must be either 'read' or 'write'.
        text (str): The text to copy onto the clipboard. Only used when action is 'write'.
    """
    action = action.lower().strip()
    valid_actions = {"read", "write"}
    
    if action not in valid_actions:
        return f"Error: Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}."

    # 1. Try Python's pyperclip library first if installed
    try:
        if action == "read":
            content = pyperclip.paste()
            return content if content else "Clipboard is currently empty."
        elif action == "write":
            pyperclip.copy(text)
            return "Successfully copied text to the clipboard."
    except Exception as e:
        # Fall through to native system CLI tools if pyperclip fails (e.g., missing Linux display hooks)
        pass

    # 2. Fallback for Linux (Wayland / X11)
    if sys.platform.startswith('linux'):
        # Try wl-clipboard (Wayland)
        wl_copy = shutil.which('wl-copy')
        wl_paste = shutil.which('wl-paste')
        if wl_copy and wl_paste:
            try:
                if action == "read":
                    proc = subprocess.run([wl_paste], capture_output=True, text=True, check=True)
                    return proc.stdout if proc.stdout else "Clipboard is currently empty."
                elif action == "write":
                    subprocess.run([wl_copy], input=text, text=True, check=True)
                    return "Successfully copied text to the clipboard via wl-copy."
            except Exception:
                pass

        # Try xclip (X11)
        xclip = shutil.which('xclip')
        if xclip:
            try:
                if action == "read":
                    proc = subprocess.run([xclip, '-selection', 'clipboard', '-o'], capture_output=True, text=True, check=True)
                    return proc.stdout if proc.stdout else "Clipboard is currently empty."
                elif action == "write":
                    subprocess.run([xclip, '-selection', 'clipboard'], input=text, text=True, check=True)
                    return "Successfully copied text to the clipboard via xclip."
            except Exception:
                pass

        return "Error: No clipboard utility found. Please install 'pyperclip' via pip, or 'wl-clipboard' / 'xclip' via your package manager."

    # 3. Fallback for macOS
    elif sys.platform == 'darwin':
        try:
            if action == "read":
                proc = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
                return proc.stdout if proc.stdout else "Clipboard is currently empty."
            elif action == "write":
                subprocess.run(['pbcopy'], input=text, text=True, check=True)
                return "Successfully copied text to the clipboard via pbcopy."
        except Exception as e:
            return f"Error using pbcopy/pbpaste on macOS: {str(e)}"

    # 4. Fallback for Windows (PowerShell)
    elif sys.platform == 'win32':
        try:
            if action == "read":
                proc = subprocess.run(
                    ['powershell', '-command', 'Get-Clipboard'], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                content = proc.stdout.rstrip('\r\n')
                return content if content else "Clipboard is currently empty."
            elif action == "write":
                # Using Set-Clipboard safely with UTF-8 input
                subprocess.run(
                    ['powershell', '-command', 'Set-Clipboard -Value $input'], 
                    input=text, 
                    text=True, 
                    check=True
                )
                return "Successfully copied text to the clipboard via PowerShell."
        except Exception as e:
            return f"Error using PowerShell clipboard on Windows: {str(e)}"

    return "Error: Could not read or write to the system clipboard on this operating system."

# Updated Tool Definition
clipboard_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'manage_clipboard',
            'description': 'Read the current text from the system clipboard or write/copy new text to it.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'action': {
                        'type': 'string',
                        'enum': ['read', 'write'],
                        'description': 'The clipboard operation to perform. Use "read" to inspect current contents, or "write" to copy new text.',
                    },
                    'text': {
                        'type': 'string',
                        'description': 'The text string to copy onto the clipboard. Only required when action is "write".',
                    },
                },
                'required': ['action'],
            },
        },
    }
]