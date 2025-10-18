import sys
from pathlib import Path

def check(path: str) -> int:
    p = Path(path)
    src = p.read_text(encoding='utf-8', errors='ignore')
    try:
        compile(src, str(p), 'exec')
    except SyntaxError as e:
        print(f"SyntaxError in {p}: {e}")
        return 1
    return 0

if __name__ == '__main__':
    code = 0
    for arg in sys.argv[1:]:
        code |= check(arg)
    sys.exit(code)

