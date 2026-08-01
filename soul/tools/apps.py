import os
import sys
import shutil
import subprocess
import shlex

def open_application(app_name: str, options: list[str] | None = None) -> dict:
    """
    Opens a local application, directory, or file on the user's computer by its name or path,
    checking the system $PATH environment variable first before using OS fallbacks.
    Returns a dictionary with 'success' (boolean) and 'message' (string).
    """
    app_name = app_name.strip()
    platform = sys.platform
    
    # Normalize options to a list
    if options is None:
        options = []
    elif isinstance(options, str):
        options = shlex.split(options)

    devnull = subprocess.DEVNULL
    suppress_kwargs = {
        'stdout': devnull,
        'stderr': devnull,
        'stdin': devnull,
        'close_fds': True
    }

    try:
        # =====================================================================
        # 1. Check System $PATH First (via shutil.which)
        # =====================================================================
        executable = shutil.which(app_name) or shutil.which(app_name.lower())
        if not executable and platform == 'win32' and not app_name.lower().endswith('.exe'):
            executable = shutil.which(f"{app_name}.exe")
            
        if executable:
            cmd = [executable] + options
            subprocess.Popen(cmd, **suppress_kwargs)
            return {
                "success": True,
                "message": f"Successfully opened '{app_name}' via system $PATH ({executable})."
            }

        # =====================================================================
        # 2. Check if input is an existing Directory or File Path
        # =====================================================================
        if os.path.exists(app_name):
            if platform == 'win32':
                os.startfile(app_name)
            elif platform == 'darwin':
                res = subprocess.run(['open', app_name] + options, capture_output=True)
                if res.returncode != 0:
                    return {"success": False, "message": f"Failed to open path: {res.stderr.decode().strip()}"}
            else:
                res = subprocess.run(['xdg-open', app_name] + options, capture_output=True)
                if res.returncode != 0:
                    return {"success": False, "message": f"Failed to open path: {res.stderr.decode().strip()}"}
            return {
                "success": True,
                "message": f"Opened path '{app_name}' successfully."
            }

        # =====================================================================
        # 3. OS-Specific Fallbacks with Validation
        # =====================================================================
        if platform == 'darwin':
            check_cmd = ['open', '-Ra', app_name]
            check_res = subprocess.run(check_cmd, capture_output=True)
            if check_res.returncode != 0:
                return {
                    "success": False,
                    "message": f"Application '{app_name}' could not be found via system $PATH or macOS search."
                }
            
            cmd = ['open', '-a', app_name]
            if options:
                cmd.extend(['--args'] + options)
            subprocess.Popen(cmd, **suppress_kwargs)
            return {
                "success": True,
                "message": f"Launched '{app_name}' via macOS 'open -a'."
            }

        elif platform == 'win32':
            try:
                os.startfile(app_name)
                return {
                    "success": True,
                    "message": f"Launched '{app_name}' via Windows os.startfile."
                }
            except OSError as e:
                options_str = " ".join(f'"{opt}"' if ' ' in opt else opt for opt in options)
                cmd_str = f'start "" "{app_name}" {options_str}'.strip()
                res = subprocess.run(cmd_str, shell=True, capture_output=True)
                if res.returncode != 0:
                    return {"success": False, "message": f"Windows failed to launch '{app_name}'."}
                return {
                    "success": True,
                    "message": f"Launched '{app_name}' via Windows shell start command."
                }

        elif platform.startswith('linux'):
            if shutil.which('gtk-launch'):
                res = subprocess.run(['gtk-launch', app_name.lower()] + options, capture_output=True)
                if res.returncode == 0:
                    return {"success": True, "message": f"Launched '{app_name}' via Linux gtk-launch."}
            
            xdg_res = subprocess.run(['xdg-open', app_name], capture_output=True)
            if xdg_res.returncode != 0:
                return {"success": False, "message": f"Linux failed to launch '{app_name}'."}
            return {
                "success": True,
                "message": f"Launched '{app_name}' via Linux xdg-open."
            }

        else:
            return {"success": False, "message": f"Unsupported operating system: {platform}"}

    except Exception as e:
        return {"success": False, "message": f"Failed to open '{app_name}'. Error: {str(e)}"}


# =====================================================================
# Tool Definition Metadata
# =====================================================================
app_tools_meta = [{
    'type': 'function',
    'function': {
        'name': 'open_application',
        'description': 'Opens a local desktop application, directory, or file path, looking through the system $PATH first.',
        'parameters': {
            'type': 'object',
            'properties': {
                'app_name': {
                    'type': 'string',
                    'description': 'The exact or common name of the application, or a directory/file path to open.',
                },
                'options': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'An optional list of command-line arguments to pass.',
                }
            },
            'required': ['app_name'],
        },
    },
}]