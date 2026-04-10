from __future__ import annotations

import time
import ctypes
from typing import Iterable

import pydirectinput
import pyperclip

# 减少默认动作延迟
pydirectinput.PAUSE = 0.02
pydirectinput.FAILSAFE = False

# Windows 鼠标滚轮事件常量
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120

def alert(text: str) -> None:
    """
    弹窗提示
    """
    return input(text)

def copy(text: str) -> None:
    """
    将文本复制到系统剪贴板
    """
    pyperclip.copy(str(text))

def move_to(x: int, y: int, duration: float = 0.0) -> None:
    """
    移动鼠标到指定位置
    """
    pydirectinput.moveTo(int(x), int(y), duration=duration)


def click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.08,
    duration: float = 0.0,
) -> None:
    """
    鼠标点击

    参数:
        x, y:
            如果提供，则先移动到该位置再点击
        button:
            left / right / middle
        clicks:
            点击次数
        interval:
            多次点击间隔
        duration:
            移动耗时
    """
    if x is not None and y is not None:
        move_to(x, y, duration=duration)
        time.sleep(0.03)

    for _ in range(int(clicks)):
        pydirectinput.mouseDown(button=button)
        time.sleep(0.03)
        pydirectinput.mouseUp(button=button)
        time.sleep(interval)


def double_click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    interval: float = 0.08,
    duration: float = 0.0,
) -> None:
    """
    双击
    """
    click(x=x, y=y, button=button, clicks=2, interval=interval, duration=duration)


def press(key: str, hold: float = 0.05) -> None:
    """
    按下并释放单个按键
    """
    pydirectinput.keyDown(key)
    time.sleep(hold)
    pydirectinput.keyUp(key)


def hotkey(*keys: str, interval: float = 0.03) -> None:
    """
    输入组合热键，例如 hotkey("ctrl", "v")
    """
    normalized_keys = _normalize_keys(keys)

    for key in normalized_keys:
        pydirectinput.keyDown(key)
        time.sleep(interval)

    for key in reversed(normalized_keys):
        pydirectinput.keyUp(key)
        time.sleep(interval)


def write(text: str, interval: float = 0.03) -> None:
    """
    输入普通字符
    适合英文、数字、符号等
    """
    if not text:
        return

    pydirectinput.write(str(text), interval=interval)


def key_down(key: str) -> None:
    """
    按下某个按键，不释放
    """
    pydirectinput.keyDown(key)


def key_up(key: str) -> None:
    """
    释放某个按键
    """
    pydirectinput.keyUp(key)

def scroll(
    clicks: int,
    x: int | None = None,
    y: int | None = None,
    duration: float = 0.0,
) -> None:
    """
    滚动鼠标滚轮

    参数:
        clicks:
            正数 = 向上滚
            负数 = 向下滚
            建议传 1、-1、2、-2 这种“步数”
        x, y:
            如果提供，则先移动到该位置再滚动
        duration:
            移动耗时
    """
    if x is not None and y is not None:
        move_to(x, y, duration=duration)
        time.sleep(0.03)

    ctypes.windll.user32.mouse_event(
        MOUSEEVENTF_WHEEL,
        0,
        0,
        int(clicks) * WHEEL_DELTA,
        0,
    )

def _normalize_keys(keys: Iterable[str]) -> list[str]:
    """
    统一热键名称
    """
    alias_map = {
        "control": "ctrl",
        "return": "enter",
        "esc": "esc",
        "del": "delete",
    }

    result: list[str] = []
    for key in keys:
        k = str(key).strip().lower()
        k = alias_map.get(k, k)
        result.append(k)

    return result