import os
import sys
import traceback
from pathlib import Path
from datetime import datetime

from src.main import main


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _prepare_runtime() -> Path:
    root = _runtime_root()
    os.chdir(root)

    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return root


def _write_crash_log(root: Path, title: str, exc: BaseException) -> None:
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    crash_path = log_dir / "crash.log"

    text = [
        "=" * 80,
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"标题: {title}",
        f"运行目录: {root}",
        f"Python: {sys.version}",
        f"Executable: {sys.executable}",
        "",
        "错误信息:",
        repr(exc),
        "",
        "完整 traceback:",
        traceback.format_exc(),
        "",
    ]

    with crash_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(text))


try:
    root = _prepare_runtime()

    if __name__ == "__main__":
        main()

except Exception as e:
    print("程序发生未处理的异常:", e)
    traceback.print_exc()

    try:
        _write_crash_log(_runtime_root(), "launcher.py 未处理异常", e)
        print("错误日志已保存到 logs/crash.log")
    except Exception as log_error:
        print("写入 crash.log 失败:", log_error)

if sys.stdin.isatty():
    input("按 Enter 键退出...")
