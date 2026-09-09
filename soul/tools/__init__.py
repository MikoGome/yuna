import importlib
import pkgutil
import inspect
from pathlib import Path

# Initialize empty containers
tools = {}
tools_meta = []

# Get the path of the current folder (where this __init__.py lives)
current_dir = Path(__file__).parent

# Iterate through all .py files in this directory
for _finder, module_name, _is_pkg in pkgutil.iter_modules([str(current_dir)]):
    
    # 1. Dynamically import the module (e.g., '.web', '.steam')
    # Using __name__ ensures it resolves the package correctly in __init__.py.
    # A single broken module (e.g., a missing optional dependency) should not
    # take down the entire tool registry.
    try:
        module = importlib.import_module(f".{module_name}", package=__name__)
    except Exception as e:
        print(f"Warning: failed to load tool module '{module_name}': {e}")
        continue
    
    # 2. Inspect everything inside the loaded module
    for name, obj in inspect.getmembers(module):
        
        # Grab Metadata: Find any list whose variable name ends with '_meta'
        if name.endswith('_meta') and isinstance(obj, list):
            tools_meta.extend(obj)
            
        # Grab Functions: Find any function that was DEFINED in this module
        # (The __module__ check prevents grabbing imported functions like 'os' or 'subprocess'.
        #  The underscore check skips private helper functions.)
        elif (
            inspect.isfunction(obj)
            and obj.__module__ == module.__name__
            and not name.startswith("_")
        ):
            tools[name] = obj

# (Optional) Print to verify it worked during development
print(f"Loaded tools: {list(tools.keys())}")