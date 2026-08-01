import os

def file_dir(file_path: str) -> str:
    return os.path.dirname(os.path.abspath(file_path))