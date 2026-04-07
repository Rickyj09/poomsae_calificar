import os

def allowed_extension(filename: str, allowed: set[str]) -> bool:
    if not filename or "." not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return ext in allowed