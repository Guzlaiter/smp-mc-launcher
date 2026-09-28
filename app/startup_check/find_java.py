import shutil
from pathlib import Path

def find_java(custom_path: str = "") -> str:
    """Ищет Java. custom_path — из настроек, если указан."""
    if custom_path:
        p = Path(custom_path)
        if p.is_file():
            return str(p)
        if p.is_dir():
            for j in p.rglob("java.exe"):
                return str(j)

    java = shutil.which("java") or shutil.which("java.exe")
    if java:
        return java

    candidates = [
        r"C:\Program Files\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
        r"E:\UTILS\JAVA",
    ]
    for base in candidates:
        p = Path(base)
        if p.exists():
            for java_exe in p.rglob("java.exe"):
                return str(java_exe)

    return False
