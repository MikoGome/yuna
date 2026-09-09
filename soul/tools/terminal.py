import os
import fnmatch

# def execute_terminal_command(command: str) -> str:
#     """
#     Executes a shell command in the terminal and returns the text output.
#     """
#     command = command.strip()

#     # =====================================================================
#     # 1. Human-in-the-Loop Safety Check
#     # =====================================================================
#     print(f"\n⚠️  The AI wants to run the following command: \n\n> {command}\n")
#     approval = input("Allow execution? (y/n/exit): ").strip().lower()
    
#     if approval in ['exit', 'quit', 'q']:
#         print("Terminating program by user request.")
#         sys.exit(0)
        
#     if approval != 'y':
#         return "Action aborted by user. Tell the user you cannot proceed without permission."

#     try:
#         # =====================================================================
#         # 2. Execute Command
#         # =====================================================================
#         result = subprocess.run(
#             command, 
#             shell=True,          
#             capture_output=True, 
#             text=True,           
#             timeout=15           
#         )
        
#         if result.returncode == 0:
#             return result.stdout if result.stdout else f"Command '{command}' executed successfully with no output."
#         else:
#             return f"Command failed with error: {result.stderr}"

#     except subprocess.TimeoutExpired:
#         return f"Error: Command '{command}' timed out after 15 seconds."
#     except Exception as e:
#         return f"Failed to execute '{command}'. Error: {str(e)}"

def list_directory(path: str = ".") -> str:
    """
    Lists the contents of a specified directory.
    """
    target_path = os.path.abspath(os.path.expanduser(path))
    
    if not os.path.exists(target_path):
        return f"Error: The path '{target_path}' does not exist."
        
    if not os.path.isdir(target_path):
        return f"Error: The path '{target_path}' is a file, not a directory."

    try:
        entries = os.listdir(target_path)
        folders, files = [], []
        
        for entry in entries:
            if os.path.isdir(os.path.join(target_path, entry)):
                folders.append(entry)
            else:
                files.append(entry)
                
        folders.sort()
        files.sort()
        
        result = [f"Contents of directory: {target_path}", "\n[Folders]:"]
        result.extend([f"  📁 {folder}/" for folder in folders] if folders else ["  (No folders)"])
        result.append("\n[Files]:")
        result.extend([f"  📄 {file}" for file in files] if files else ["  (No files)"])
            
        return "\n".join(result)
        
    except PermissionError:
        return f"Error: Permission denied to access '{target_path}'."
    except Exception as e:
        return f"Error: An unexpected error occurred while accessing '{target_path}': {str(e)}"

def find_applications(path: str, iname_pattern: str, file_type: str = "d", max_depth: int = None) -> str:
    """
    Pure Python cross-platform implementation to locate applications/files.
    Behaves similarly to the Unix `find -iname` command but works universally
    on Windows, macOS, and Linux without risking shell execution.
    """
    target_path = os.path.abspath(os.path.expanduser(path))
    
    if not os.path.exists(target_path):
        return f"Error: The path '{target_path}' does not exist."

    matches = []
    # Count the depth of the starting directory to track relative depth safely
    base_depth = target_path.rstrip(os.sep).count(os.sep)
    
    # Normalize pattern to lowercase for strict case-insensitivity
    pattern = iname_pattern.lower()

    try:
        for root, dirs, files in os.walk(target_path):
            current_depth = root.rstrip(os.sep).count(os.sep) - base_depth
            
            # Check directories (essential for macOS .app bundles or Windows folders)
            if file_type in ("d", None):
                for d in dirs:
                    if fnmatch.fnmatch(d.lower(), pattern):
                        matches.append(os.path.join(root, d))
                        
            # Check files (essential for Windows .exe or Linux binaries)
            if file_type in ("f", None):
                for f in files:
                    if fnmatch.fnmatch(f.lower(), pattern):
                        matches.append(os.path.join(root, f))
            
            # Prune directories in-place to prevent os.walk from descending further
            # if we have reached the max_depth limit.
            if max_depth is not None and current_depth >= (max_depth - 1):
                dirs.clear()

        if matches:
            return "\n".join(matches)
        return "No matching applications or files found."

    except PermissionError:
        return f"Error: Permission denied while scanning parts of '{target_path}'."
    except Exception as e:
        return f"Failed to execute find search. Error: {str(e)}"


# =====================================================================
# Tool Definition Metadata
# =====================================================================
terminal_tools_meta = [
    # {
    #     'type': 'function',
    #     'function': {
    #         'name': 'execute_terminal_command',
    #         'description': 'Executes a shell command in the system terminal and returns the text output. Use this to navigate the file system, read files, or check system status.',
    #         'parameters': {
    #             'type': 'object',
    #             'properties': {
    #                 'command': {
    #                     'type': 'string',
    #                     'description': 'The exact terminal command to execute (e.g., "ls -la", "cat file.txt", "pwd").',
    #                 },
    #             },
    #             'required': ['command'],
    #         },
    #     },
    # },
    {
        'type': 'function',
        'function': {
            'name': 'list_directory',
            'description': 'List the files and folders inside a specified directory. Useful for exploring the file system to find a specific route or file.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': 'The absolute or relative path to the directory to list. Use "." for the current directory.',
                    }
                },
                'required': ['path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'find_applications',
            'description': 'Cross-platform tool that searches the file system to locate applications or files case-insensitively. Safely returns paths without invoking system shells.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': "The absolute or relative path to the directory to start searching in (e.g., '/Applications', 'C:\\Program Files', or '/')."
                    },
                    'iname_pattern': {
                        'type': 'string',
                        'description': "The case-insensitive name or wildcard pattern of the application to find (e.g., '*.app', 'firefox.app', '*.exe', or 'discord*')."
                    },
                    'file_type': {
                        'type': 'string',
                        'description': "The type of item to look for. Use 'd' for directories (macOS .app bundles) or 'f' for standard executable files (Linux/Windows).",
                        'enum': ["f", "d"]
                    },
                    'max_depth': {
                        'type': 'integer',
                        'description': "The maximum directory depth to search to prevent infinite or overly long traversals (e.g., 3 or 5)."
                    }
                },
                'required': ['path', 'iname_pattern']
            },
        },
    }
]