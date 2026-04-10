from __future__ import annotations

import time
import ctypes
from typing import Optional

import psutil
import pygetwindow as gw
import win32gui
import win32process

user32 = ctypes.windll.user32


def _get_all_processes() -> list[dict]:
    """
    获取当前所有进程
    """
    result = []

    for proc in psutil.process_iter(["pid", "name", "exe", "status"]):
        try:
            info = proc.info
            result.append({
                "pid": info.get("pid"),
                "name": info.get("name"),
                "exe": info.get("exe"),
                "status": info.get("status"),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return result


def find_processes_by_keyword(keyword: str) -> list[dict]:
    """
    根据关键字查找进程名或 exe 路径
    """
    keyword = keyword.lower().strip()
    result = []

    for proc in psutil.process_iter(["pid", "name", "exe", "status"]):
        try:
            info = proc.info
            name = (info.get("name") or "").lower()
            exe = (info.get("exe") or "").lower()

            if keyword in name or keyword in exe:
                result.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "exe": info.get("exe"),
                    "status": info.get("status"),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return result


def find_pids_by_keyword(keyword: str) -> list[int]:
    """
    根据关键字查找所有匹配进程的 pid
    """
    processes = find_processes_by_keyword(keyword)
    return [p["pid"] for p in processes if p.get("pid") is not None]


def find_first_pid_by_keyword(keyword: str) -> Optional[int]:
    """
    根据关键字查找第一个匹配进程的 pid
    """
    pids = find_pids_by_keyword(keyword)
    if not pids:
        return None
    return pids[0]


def find_windows_by_title(title_keyword: str) -> list:
    """
    根据窗口标题关键字查找窗口
    """
    return gw.getWindowsWithTitle(title_keyword)


def find_first_window_by_title(title_keyword: str):
    """
    根据窗口标题关键字查找第一个窗口
    """
    wins = find_windows_by_title(title_keyword)
    if not wins:
        return None
    return wins[0]


def find_hwnds_by_pid(pid: int) -> list[int]:
    """
    根据 pid 查找该进程对应的可见窗口句柄列表
    """
    hwnds: list[int] = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return

        try:
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid == pid:
                hwnds.append(hwnd)
        except Exception:
            pass

    win32gui.EnumWindows(callback, None)
    return hwnds


def get_window_title_by_pid(pid: int) -> Optional[str]:
    """
    通过 pid 获取一个可见窗口的标题
    """
    hwnds = find_hwnds_by_pid(pid)
    if not hwnds:
        return None

    for hwnd in hwnds:
        try:
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                return title
        except Exception:
            continue

    return None


def activate_window(win, restore_if_minimized: bool = True, delay: float = 1.0) -> bool:
    """
    激活 pygetwindow 的窗口对象
    """
    if win is None:
        return False

    try:
        if restore_if_minimized and win.isMinimized:
            win.restore()
            time.sleep(0.3)

        try:
            win.activate()
        except Exception:
            pass

        try:
            user32.SetForegroundWindow(win._hWnd)
        except Exception:
            pass

        time.sleep(delay)
        return True
    except Exception:
        return False


def activate_window_by_title(title_keyword: str, delay: float = 1.0):
    """
    通过窗口标题关键字查找并激活窗口
    """
    win = find_first_window_by_title(title_keyword)
    if not win:
        return None

    ok = activate_window(win, delay=delay)
    if not ok:
        return None

    return win


def activate_window_by_pid(pid: int, delay: float = 1.0) -> bool:
    """
    通过 pid 激活窗口
    """
    hwnds = find_hwnds_by_pid(pid)
    if not hwnds:
        return False

    target_hwnd = None

    for hwnd in hwnds:
        try:
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                target_hwnd = hwnd
                break
        except Exception:
            continue

    if target_hwnd is None:
        target_hwnd = hwnds[0]

    try:
        if win32gui.IsIconic(target_hwnd):
            win32gui.ShowWindow(target_hwnd, 9)  # SW_RESTORE

        win32gui.SetForegroundWindow(target_hwnd)
        time.sleep(delay)
        return True
    except Exception:
        return False