import os
import sys
import shutil
import subprocess
import shlex

def open_application(app_name: str, options: list[str] | None = None) -> dict:
    """
    Opens a local application on the user's computer by its name, 
    optionally passing command-line arguments.
    Returns a dictionary with 'success' (boolean) and 'message' (string).
    """
    app_name = app_name.strip()
    platform = sys.platform
    
    # Normalize options to a list
    if options is None:
        options = []
    elif isinstance(options, str):
        # Fallback if a string is passed instead of a list
        options = shlex.split(options)

    # Arguments to suppress I/O for direct execution
    devnull = subprocess.DEVNULL
    suppress_kwargs = {
        'stdout': devnull,
        'stderr': devnull,
        'stdin': devnull
    }

    try:
        # =====================================================================
        # 1. Check System PATH First
        # =====================================================================
        executable = shutil.which(app_name)
        
        if not executable:
            executable = shutil.which(app_name.lower())
            
        if not executable and platform == 'win32' and not app_name.lower().endswith('.exe'):
            executable = shutil.which(f"{app_name}.exe")
            
        if executable:
            # Popen is safe here because shutil.which already confirmed the file exists
            cmd = [executable] + options
            subprocess.Popen(cmd, **suppress_kwargs)
            return {
                "success": True, 
                "message": f"Successfully opened '{app_name}' via system PATH ({executable}) with options: {options}."
            }

        # =====================================================================
        # 2. OS-Specific Fallbacks (If not found in PATH)
        # =====================================================================
        
        if platform == 'darwin':
            # macOS 'open -a' uses '--args' to pass parameters to the application
            cmd = ['open', '-a', app_name]
            if options:
                cmd.extend(['--args'] + options)
                
            result = subprocess.run(
                cmd, 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Opened '{app_name}' via macOS 'open -a' with options: {options}."}
            else:
                return {"success": False, "message": f"macOS could not find '{app_name}'. {result.stderr.strip()}"}

        elif platform == 'win32':
            # Escape options for the Windows shell
            options_str = " ".join(f'"{opt}"' if ' ' in opt else opt for opt in options)
            cmd_str = f'start "" "{app_name}" {options_str}'.strip()
            
            result = subprocess.run(
                cmd_str, 
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Attempted to launch '{app_name}' via Windows shell with options: {options}."}
            else:
                return {"success": False, "message": f"Windows could not find '{app_name}'."}

        elif platform.startswith('linux'):
            # Try gtk-launch first (supports passing arguments in most modern desktop environments)
            result = subprocess.run(
                ['gtk-launch', app_name.lower()] + options, 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Launched '{app_name}' via gtk-launch with options: {options}."}
            
            # Fallback to xdg-open. Note: xdg-open expects a file/URL, so we pass the first option if available.
            xdg_cmd = ['xdg-open']
            if options:
                xdg_cmd.append(options[0])
            else:
                xdg_cmd.append(app_name)
                
            result2 = subprocess.run(
                xdg_cmd, 
                capture_output=True, text=True
            )
            if result2.returncode == 0:
                return {"success": True, "message": f"Launched target via xdg-open."}
            
            return {"success": False, "message": f"Linux could not find or open '{app_name}'."}
            
        else:
            return {"success": False, "message": f"Unsupported operating system: {platform}"}

    except Exception as e:
        return {"success": False, "message": f"Failed to open '{app_name}'. Error: {str(e)}"}


# =====================================================================
# 2. Ollama Tool Definition Metadata
# =====================================================================
app_tools_meta = [{
    'type': 'function',
    'function': {
        'name': 'open_application',
        'description': 'Opens a local desktop application or directory on the user\'s computer by name, with support for command-line options.',
        'parameters': {
            'type': 'object',
            'properties': {
                'app_name': {
                    'type': 'string',
                    'description': 'The exact or common name of the application or directory to open (e.g., Chrome, Notepad, Code).',
                },
                'options': {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    },
                    'description': 'An optional list of command-line arguments to pass to the application (e.g., ["https://google.com"] or ["/path/to/file.txt", "--read-only"]).',
                }
            },
            'required': ['app_name'],
        },
    },
}]