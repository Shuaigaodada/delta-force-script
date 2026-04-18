import os
import sys
import traceback
from pathlib import Path

from src.main import main


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _prepare_runtime() -> None:
    os.chdir(_runtime_root())


try:
    _prepare_runtime()
    if __name__ == "__main__":
        main()
except Exception as e:
    print("程序发生未处理的异常:", e)
    traceback.print_exc()
finally:
    input("按 Enter 键退出...")
