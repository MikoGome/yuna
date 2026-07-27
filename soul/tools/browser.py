import os
import sys
import shutil
import webbrowser
import subprocess

def open_browser(url: str, incognito: bool = False) -> str:
    """
    Opens the web browser to a specified URL.
    
    Args:
        url (str): The web address to open (e.g., 'https://www.wikipedia.org').
        incognito (bool): Whether to open in incognito/private mode.
    """
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # If normal mode, rely entirely on Python's built-in OS routing
    if not incognito:
        webbrowser.open(url)
        return f"Successfully opened default browser to {url}"

    # Map of common browser executables to their incognito flags
    browser_flags = {
        'chrome': '--incognito',
        'google-chrome': '--incognito',
        'firefox': '--private-window',
        'msedge': '-InPrivate',
        'brave': '--incognito',
        'opera': '--private'
    }

    # 1. Try to find a supported browser in the system PATH (Windows/Linux)
    for browser, flag in browser_flags.items():
        executable = shutil.which(browser)
        # Handle Windows .exe extensions
        if not executable and sys.platform == 'win32':
            executable = shutil.which(f"{browser}.exe")
            
        if executable:
            try:
                subprocess.Popen([executable, flag, url])
                return f"Successfully opened {browser} in incognito mode to {url}"
            except Exception:
                continue
    
    # 2. Try common macOS application paths
    if sys.platform == 'darwin':
        osx_browsers = {
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome': '--incognito',
            '/Applications/Firefox.app/Contents/MacOS/firefox': '--private-window',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge': '-InPrivate',
            '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser': '--incognito'
        }
        for app_path, flag in osx_browsers.items():
            if os.path.exists(app_path):
                try:
                    subprocess.Popen([app_path, flag, url])
                    return f"Successfully opened incognito browser to {url}"
                except Exception:
                    continue

    # 3. Fallback: If no known browser is found for incognito, open normally
    webbrowser.open(url)
    return f"Opened default browser (could not apply incognito mode) to {url}"

# Updated Tool Definition
browser_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'open_browser',
            'description': 'Open the web browser to a specific URL. Use incognito mode only if explicitly requested.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'url': {
                        'type': 'string',
                        'description': 'The full URL to open, including https://',
                    },
                    'incognito': {
                        'type': 'boolean',
                        'description': 'Set to true to open in incognito mode, false otherwise.',
                    },
                },
                'required': ['url'],
            },
        },
    }
]