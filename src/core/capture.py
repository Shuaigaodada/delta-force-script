import cv2
import numpy as np
from mss import mss
from typing import Optional
import pygetwindow as gw
import win32gui

from src.core import processes


def fullscreen(monitor_index: int = 1) -> tuple[np.ndarray, dict]:
    """
    截取整块屏幕

    参数:
        monitor_index:
            mss().monitors[1] 是主屏
            monitors[0] 是所有屏幕的总区域

    返回:
        (BGR图像, monitor信息)
    """
    with mss() as sct:
        monitor = sct.monitors[monitor_index]
        shot = sct.grab(monitor)
        img = np.array(shot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img, monitor


def region(left: int, top: int, width: int, height: int) -> tuple[np.ndarray, dict]:
    """
    截取指定区域
    """
    region = {
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height),
    }

    with mss() as sct:
        shot = sct.grab(region)
        img = np.array(shot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img, region


def window(win) -> tuple[np.ndarray, dict]:
    """
    截取 pygetwindow 获取到的窗口
    """
    left = int(win.left)
    top = int(win.top)
    width = int(win.width)
    height = int(win.height)

    return region(left, top, width, height)


def window_by_title(title_keyword: str) -> tuple[Optional[np.ndarray], Optional[dict], Optional[object]]:
    """
    根据窗口标题关键字截取窗口
    """
    wins = gw.getWindowsWithTitle(title_keyword)
    if not wins:
        return None, None, None

    win = wins[0]
    img, region = window(win)
    return img, region, win

def window_by_pid(pid: int) -> tuple[Optional[np.ndarray], Optional[dict], Optional[int]]:
    """根据进程 ID 截取可见窗口。"""
    hwnds = processes.find_hwnds_by_pid(pid)
    if not hwnds:
        return None, None, None

    target_hwnd = None

    # 优先选标题非空的窗口
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
        left, top, right, bottom = win32gui.GetWindowRect(target_hwnd)
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            return None, None, target_hwnd

        img, reg = region(left, top, width, height)
        return img, reg, target_hwnd
    except Exception:
        return None, None, target_hwnd
