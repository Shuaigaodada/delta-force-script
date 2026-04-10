import sys
import ctypes
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


def relaunch_launcher_as_admin(launcher_path: str | None = None) -> int:
    """
    以管理员权限重新启动 launcher.py

    返回:
        ShellExecuteW 的返回值
        > 32 表示成功发起
        <= 32 表示失败
    """
    if launcher_path is None:
        # 默认从当前文件位置反推项目根目录，再找到 launcher.py
        project_root = pathlib.Path(__file__).resolve().parents[2]
        launcher = project_root / "launcher.py"
    else:
        launcher = pathlib.Path(launcher_path).resolve()

    if not launcher.exists():
        raise FileNotFoundError(f"找不到 launcher.py: {launcher}")

    python_exe = sys.executable
    params = f'"{str(launcher)}"'

    ret = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        python_exe,
        params,
        None,
        1
    )
    return int(ret)


def ensure_admin_or_relaunch_launcher(launcher_path: str | None = None) -> bool:
    """
    如果当前已经是管理员，返回 True
    如果当前不是管理员，则尝试以管理员权限重启 launcher.py，然后当前进程退出

    返回:
        True: 当前已经是管理员，可继续执行
        False: 提权启动失败
    """
    if is_admin():
        return True

    logger.info("当前不是管理员权限，正在尝试以管理员权限重新启动 launcher.py ...")

    try:
        ret = relaunch_launcher_as_admin(launcher_path)
    except Exception as e:
        logger.error("重新启动 launcher.py 失败：%s", e)
        return False

    if ret <= 32:
        logger.error("提权失败，ShellExecuteW 返回值: %d", ret)
        return False

    logger.info("已成功发起管理员 launcher，当前进程即将退出。")
    sys.exit(0)