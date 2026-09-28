import shutil
from pathlib import Path
from ..config import load_config, save_config

def find_java(custom_path: str = "") -> str:
    print('find_java')    
    """Ищет Java. custom_path — из настроек, если указан."""
    if custom_path:
        p = Path(custom_path)
        if p.is_file():
            return str(p)
        if p.is_dir():
            for j in p.rglob("java.exe"):
                return str(j)
    print('кастом не найден')    

    java = shutil.which("java") or shutil.which("java.exe")
    if java:
        print(java)    
        
        print('1')        
        cfg = load_config()
        print('2')    
        cfg['java_path'] = str(java)
        print('3')    
        save_config(cfg)
        print('4')    
        return java
    print('шатил не найден')    

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
                cfg = load_config()
                cfg['java_path'] = str(java_exe)
                save_config(cfg)
                return str(java_exe)
    print('кондидаты не найдены')    

    return False
