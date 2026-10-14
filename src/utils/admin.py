import sys
import ctypes
import os
import pathlib
from src.utils.loggers import logger


def is_admin() -> bool:
    """
    判断当前进程是否为管理员权限
    """
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _project_root_for_source() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _launcher_path_for_source(launcher_path: str | None = None) -> pathlib.Path:
    if launcher_path is None:
        return _project_root_for_source() / "launcher.py"
    return pathlib.Path(launcher_path).resolve()


def relaunch_launcher_as_admin(launcher_path: str | None = None) -> int:
    """
    以管理员权限重新启动 launcher。

    源码模式:
        使用当前 Python 解释器重新运行 launcher.py
    打包模式:
        直接以管理员权限重新启动当前 exe

    返回:
        ShellExecuteW 的返回值
        > 32 表示成功发起
        <= 32 表示失败
    """
    if getattr(sys, "frozen", False):
        current_exe = pathlib.Path(sys.executable).resolve()
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            str(current_exe),
            None,
            str(current_exe.parent),
            1,
        )
        return int(ret)

    launcher = _launcher_path_for_source(launcher_path)
    if not launcher.exists():
        raise FileNotFoundError(f"找不到 launcher.py: {launcher}")

    python_exe = sys.executable
    params = f'"{str(launcher)}"'

    ret = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        python_exe,
        params,
        str(launcher.parent),
        1,
    )
    return int(ret)


def ensure_admin_or_relaunch_launcher(launcher_path: str | None = None) -> bool:
    """
    如果当前已经是管理员，返回 True。
    如果当前不是管理员，则尝试以管理员权限重启 launcher，然后当前进程退出。

    返回:
        True: 当前已经是管理员，可继续执行
        False: 提权启动失败
    """
    if is_admin():
        return True

    if os.environ.get("DELTA_FORCE_ELEVATION_ATTEMPTED") == "1":
        logger.error("已尝试提权，但新进程仍没有管理员权限，停止重复启动")
        return False

    logger.info("当前不是管理员权限，正在尝试以管理员权限重新启动 launcher ...")

    try:
        os.environ["DELTA_FORCE_ELEVATION_ATTEMPTED"] = "1"
        ret = relaunch_launcher_as_admin(launcher_path)
    except Exception as e:
        logger.error("重新启动 launcher 失败：%s", e)
        return False

    if ret <= 32:
        logger.error("提权失败，ShellExecuteW 返回值: %d", ret)
        return False

    logger.info("已成功发起管理员进程，当前进程即将退出。")
    sys.exit(0)
