from __future__ import annotations

import json
import time
import pathlib
import sys
import numpy as np
from typing import Optional

from src.core import input
from src.core import vision
from src.core import capture
from src.core import processes
from src.utils.loggers import logger

def _app_root() -> pathlib.Path:
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parents[2]


APP_ROOT = _app_root()
DATA_DIR = APP_ROOT / "data"
TEMPLATE_DIR = DATA_DIR / "templates" / "delta_force"
ACCOUNT_FILE = DATA_DIR / "accounts.json"


launcher_pid = None
client_pid = None

accounts: list[dict] = []



def read_all_accounts() -> list[dict]:
    """
    读取所有账号信息
    """
    global accounts

    if accounts:
        return accounts

    try:
        with ACCOUNT_FILE.open("r", encoding="utf-8") as f:
            accounts = json.load(f)
    except FileNotFoundError:
        accounts = []
        logger.error(f"账号文件 {ACCOUNT_FILE} 不存在，已创建空账号列表")
    except json.JSONDecodeError:
        accounts = []
        logger.error(f"账号文件 {ACCOUNT_FILE} 格式错误，已创建空账号列表")

    return accounts


def debug_delta_force_processes() -> None:
    """
    调试输出：查看和 Delta Force 相关的所有候选进程
    """
    keywords = [
        "delta_force_launcher",
        "launcher",
    ]

    seen: dict[int, dict] = {}

    for kw in keywords:
        print(f"\n关键词: {kw}")
        matches = processes.find_processes_by_keyword(kw)
        for item in matches:
            pid = item.get("pid")
            if pid is None:
                continue
            if pid not in seen:
                seen[pid] = item
                print(item)


def find_best_delta_force_process() -> Optional[dict]:
    """
    查找最像 三角洲行动启动器 的进程
    """
    keywords = [
        "delta_force_launcher",
        "launcher",
    ]
    logger.info("正在查找 三角洲行动 相关进程...")

    result: list[dict] = []
    for kw in keywords:
        logger.info(f"使用关键词 '{kw}' 查找相关进程...")
        result.extend(processes.find_processes_by_keyword(kw))

    unique: dict[int, dict] = {}
    for item in result:
        pid = item.get("pid")
        if pid is not None:
            unique[pid] = item

    candidates = list(unique.values())
    if not candidates:
        return None

    def score(proc: dict) -> tuple[int, int]:
        name = (proc.get("name") or "").lower()
        exe = (proc.get("exe") or "").lower()

        s = 0

        # 最优先：精确命中真实启动器
        if name == "delta_force_launcher.exe":
            s += 1000

        if "delta_force_launcher" in name:
            s += 500
        if "delta_force_launcher" in exe:
            s += 400

        # 次优先：delta_force 主串
        if "delta_force" in name:
            s += 200
        if "delta_force" in exe:
            s += 150

        # 路径里出现带空格的 Delta Force，只给较低分
        if "delta force" in name:
            s += 80
        if "delta force" in exe:
            s += 60

        if "三角洲" in name:
            s += 50
        if "三角洲" in exe:
            s += 40

        if "launcher" in name:
            s += 20
        if "launcher" in exe:
            s += 10

        # 明确降权常见误命中子进程
        if name == "browser.exe":
            s -= 500
        if name == "taslogin.exe":
            s -= 500

        # 保险：路径里出现 qbblinktrial / tenprotect 的都降权
        if "qbblinktrial" in exe:
            s -= 300
        if "tenprotect" in exe:
            s -= 300

        return (s, -(proc.get("pid") or 0))

    logger.info(f"找到 {len(candidates)} 个 三角洲行动 相关候选进程，正在评分排序...")
    candidates.sort(key=score, reverse=True)
    best = candidates[0]

    logger.info(
        f"最佳三角洲候选进程: pid={best.get('pid')}, "
        f"name={best.get('name')}, exe={best.get('exe')}"
    )
    return best

def find_best_delta_force_client_process(retry_interval: float = 0.5) -> Optional[dict]:
    """
    查找最像 三角洲行动 客户端 的进程
    真实主进程通常是:
    DeltaForceClient-Win64-Shipping.exe
    """
    keywords = [
        "deltaforceclient-win64-shipping",

    ]

    while True:
        logger.info("正在查找 三角洲行动 客户端 相关进程...")

        result: list[dict] = []
        for kw in keywords:
            logger.info(f"使用关键词 '{kw}' 查找客户端进程...")
            result.extend(processes.find_processes_by_keyword(kw))

        unique: dict[int, dict] = {}
        for item in result:
            pid = item.get("pid")
            if pid is not None:
                unique[pid] = item

        candidates = list(unique.values())
        if not candidates:
            logger.warning("未找到 三角洲行动 客户端 相关进程")
            logger.info(f"{retry_interval} 秒后重试...")
            time.sleep(retry_interval)
            continue

        def score(proc: dict) -> tuple[int, int]:
            name = (proc.get("name") or "").lower()
            exe = (proc.get("exe") or "").lower()

            s = 0

            # 最优先：精确命中真实客户端
            if name == "deltaforceclient-win64-shipping.exe":
                s += 1500

            if "deltaforceclient-win64-shipping" in name:
                s += 1000
            if "deltaforceclient-win64-shipping" in exe:
                s += 900

            if "deltaforceclient" in name:
                s += 500
            if "deltaforceclient" in exe:
                s += 450

            if "shipping" in name:
                s += 200
            if "shipping" in exe:
                s += 180

            if "delta force" in exe:
                s += 50
            if "deltaforce" in exe:
                s += 40

            # 排除启动器和常见子进程
            if name == "delta_force_launcher.exe":
                s -= 1500
            if name == "browser.exe":
                s -= 1000
            if name == "taslogin.exe":
                s -= 1000

            if "qbblinktrial" in exe:
                s -= 800
            if "tenprotect" in exe:
                s -= 800
            if "launcher" in exe:
                s -= 300

            return (s, -(proc.get("pid") or 0))

        logger.info(f"找到 {len(candidates)} 个 三角洲行动 客户端 候选进程，正在评分排序...")
        candidates.sort(key=score, reverse=True)
        best = candidates[0]

        logger.info(
            f"最佳三角洲客户端候选进程: pid={best.get('pid')}, "
            f"name={best.get('name')}, exe={best.get('exe')}"
        )
        return best



def activate_delta_force() -> bool:
    """
    查找并激活 三角洲行动启动器/窗口
    """
    global launcher_pid
    if launcher_pid is not None:
        logger.info(f"已知 launcher_pid={launcher_pid}，尝试激活对应窗口...")
        ok = processes.activate_window_by_pid(launcher_pid)
        if ok:
            logger.info("已激活 三角洲行动 窗口")
            return True
        else:
            logger.warning("通过已知 launcher_pid 激活窗口失败，可能进程已重启，重置 launcher_pid 并继续查找")
            launcher_pid = None
    delta_force = find_best_delta_force_process()
    if not delta_force:
        logger.error("未找到 三角洲行动 相关进程")
        return False

    delta_force_pid = delta_force["pid"]
    logger.info(
        f"找到 三角洲行动 进程: pid={delta_force_pid}, "
        f"name={delta_force.get('name')}"
    )
    launcher_pid = delta_force_pid

    ok = processes.activate_window_by_pid(delta_force_pid)
    if not ok:
        logger.error("通过 pid 激活 三角洲行动 窗口失败")
        return False

    logger.info("已激活 三角洲行动 窗口")
    return True



def _capture_screen(pid: int, retry_interval: float = 0.5, warn: str = ""):
    screen, region, hwnd = capture.window_by_pid(pid)
    if screen is None or region is None:
        logger.warning(warn)
        logger.info(f"{retry_interval + 1} 秒后重试...")
        time.sleep(retry_interval + 1)
        return None, None, None
    return screen, region, hwnd

def available_delta_force_window(retry_interval: float = 0.5) -> Optional[dict]:
    """
    确保 三角洲行动 窗口可用并已激活，返回进程信息
    """
    global launcher_pid
    if launcher_pid is not None:
        logger.info(f"已知 launcher_pid={launcher_pid}，尝试激活对应窗口...")
        ok = processes.activate_window_by_pid(launcher_pid)
        if ok:
            logger.info("已激活 三角洲行动 窗口")
            return {"pid": launcher_pid}
        else:
            logger.warning("通过已知 launcher_pid 激活窗口失败，可能进程已重启，重置 launcher_pid 并继续查找")
            launcher_pid = None
    while True:
        delta_force = find_best_delta_force_process()
        if not delta_force:
            logger.error("未找到 三角洲行动 相关进程，请先启动 三角洲行动")
            logger.info(f"{retry_interval} 秒后重试...")
            time.sleep(retry_interval)
            continue

        delta_force_pid = delta_force["pid"]
        logger.info(
            f"找到 三角洲行动 进程: pid={delta_force_pid}, "
            f"name={delta_force.get('name')}, exe={delta_force.get('exe')}"
        )

        launcher_pid = delta_force_pid
        
        ok = processes.activate_window_by_pid(delta_force_pid)
        if not ok:
            logger.error("激活 三角洲行动 窗口失败")
            logger.info(f"{retry_interval} 秒后重试...")
            time.sleep(retry_interval)
            continue

        break

    logger.info("已激活 三角洲行动启动器")
    return delta_force
    
def activate_delta_force_client(pid: int = None, retry_interval: float = 0.5) -> bool:
    if pid is None:
        client = find_best_delta_force_client_process(retry_interval=retry_interval)
        if not client:
            logger.error("未找到 三角洲行动 客户端 相关进程")
            return False

        pid = client["pid"]
        logger.info(
            f"找到 三角洲行动 客户端 进程: pid={pid}, "
            f"name={client.get('name')}, exe={client.get('exe')}"
        )

    ok = processes.activate_window_by_pid(pid)
    if not ok:
        logger.error("通过 pid 激活 三角洲行动 客户端 窗口失败")
        return False

    logger.info("已激活 三角洲行动 客户端 窗口")
    return True

def load_template(template_name: str) -> Optional[np.ndarray]:
    """
    加载模板图片
    """
    template_path = TEMPLATE_DIR / template_name
    template = vision.image_read(str(template_path))
    if template is None:
        logger.error(f"未找到模板图片: {template_path}")
        return None
    return template

def login_account(usr_id: str, retry_interval: float = 0.5) -> bool:
    """
    切换账号
    """
    global launcher_pid
    launcher_pid = None
    delta_force = available_delta_force_window(retry_interval=retry_interval)
    delta_force_pid = delta_force["pid"]
    logger.info(f"账号 ID: {usr_id}")
    
    
    
    TEMPLATE_QQ = load_template("qq_login.png")
    TEMPLATE_WECHAT = load_template("wechat_login.png")
    TEMPLATE_QQ_CLEARLY_LOGIN = load_template("qq_clearly_login.png")
    TEMPLATE_SWITCH = load_template("switch_qq.png")
    TEMPLATE_PASS = load_template("qq_pass.png")
    TEMPLATE_NOPASS = load_template("qq_nopass.png")
    TEMPLATE_CONFIRM_BTN = load_template("confirm_btn.png")
    TEMPLATE_START_GAME = load_template("start_game.png")
    
    while True:
        screen, region, hwnd = _capture_screen(delta_force_pid, retry_interval, warn="无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
        if screen is None or region is None:
            logger.warning("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡，重试中...")
            continue
        
        found, _, _, _ = vision.find_template(screen, TEMPLATE_START_GAME, threshold=0.7, origin=(region["left"], region["top"]))
        if found:
            logger.warning("检测到已登录状态，可能当前账号已登录或界面异常，尝试执行退出账号流程")
            quit_ok = quit_account()
            if not quit_ok:
                logger.error("退出账号流程执行失败，无法继续登录新账号")
                return False
            return login_account(usr_id, retry_interval=retry_interval)
        break

    while True:
        screen, region, hwnd = _capture_screen(delta_force_pid, retry_interval, warn="无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
        if screen is None or region is None:
            logger.warning("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡，重试中...")
            continue

        origin = (region["left"], region["top"])

        qq_found, qq_score, qq_top_left, qq_bottom_right = vision.find_template(
            screen,
            TEMPLATE_QQ,
            threshold=0.71,
            origin=origin,
        )
        wechat_found, wechat_score, wechat_top_left, wechat_bottom_right = vision.find_template(
            screen,
            TEMPLATE_WECHAT,
            threshold=0.71,
            origin=origin,
        )

        logger.info(
            f"QQ检测: found={qq_found}, score={qq_score:.4f}, "
        )
        logger.info(
            f"微信检测: found={wechat_found}, score={wechat_score:.4f}, "
        )
        
        if 0.7 > qq_score > 0.6:
            qc_found, qc_score, _, _ = vision.find_template(
                screen,
                TEMPLATE_QQ_CLEARLY_LOGIN,
                threshold=0.8,
                origin=origin,
            )
            qq_found = qc_found if qc_found else qq_found
            qq_score = qc_score if qc_found else qq_score
            logger.info(
                f"清晰QQ检测: found={qc_found}, score={qc_score:.4f}, "
            )

        if not qq_found and not wechat_found:
            logger.warning("未检测到 QQ 或 微信登录按钮，重试中...")
            time.sleep(retry_interval)
            continue

        # 已经是QQ登录
        if qq_found and (not wechat_found or qq_score >= wechat_score):
            logger.info("当前更接近 QQ 登录，继续执行后续逻辑")
            break

        # 当前是微信登录，需要切换到QQ
        if wechat_found and wechat_score > qq_score:
            logger.info("当前更接近 微信登录，准备点击“切换到QQ登录”按钮")

            switch_found, switch_score, switch_top_left, switch_bottom_right = vision.find_template(
                screen,
                TEMPLATE_SWITCH,
                threshold=0.85,
                origin=origin,
            )

            logger.info(
                f"切换QQ按钮检测: found={switch_found}, score={switch_score:.4f}, "
                f"top_left={switch_top_left}, bottom_right={switch_bottom_right}"
            )

            if not switch_found or switch_top_left is None or switch_bottom_right is None:
                logger.error("未找到“切换到QQ登录”按钮")
                time.sleep(retry_interval)
                continue

            click_x, click_y = vision.box_center(
                switch_top_left,
                switch_bottom_right,
                offset=(0, 0),
            )

            logger.info(f"准备点击切换按钮，绝对坐标=({click_x}, {click_y})")
            input.click(click_x, click_y)
            logger.info("已点击“切换到QQ登录”按钮")

            time.sleep(1.0)
            continue
    screen, region, hwnd = capture.window_by_pid(delta_force_pid)
    if screen is None or region is None:
        logger.error("无法截取 三角洲行动 登录窗口")
        return False
    origin = (region["left"], region["top"])
    input.click(origin[0] + 10, origin[1] + 10) # 点击窗口内任意位置以确保窗口获得焦点
    time.sleep(0.5)
    input.hotkey("tab")
    time.sleep(0.5)
    input.copy(usr_id)
    input.hotkey("ctrl", "a")
    time.sleep(0.5)
    input.hotkey("ctrl", "v")
    time.sleep(0.5)
    
    while True:
        screen, region, hwnd = _capture_screen(delta_force_pid, retry_interval, warn="无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
        if screen is None or region is None:
            continue

        origin = (region["left"], region["top"])

        pfound, pscore, p_top_left, p_bottom_right = vision.find_template(screen, TEMPLATE_PASS, threshold=0.75, origin=origin)
        npfound, npscore, np_top_left, np_bottom_right = vision.find_template(screen, TEMPLATE_NOPASS, threshold=0.75, origin=origin)
        
        logger.info(
            f"密码框检测: found={pfound}, score={pscore:.4f}, "
            f"nopass_found={npfound}, nopass_score={npscore:.4f}"
        )
        if not pfound and not npfound:
            logger.warning("未检测到 QQ 密码输入框，重试中...")
            time.sleep(retry_interval)
            continue
        if npscore > pscore:
            logger.info("检测到无密码，可能是第一次登入，手动输入密码")
            input.hotkey("tab")
            input.alert("由于三角洲保护限制，无法自动输入密码，请手动输入密码后点击登入按钮，在此界面按回车")
            while True:
                ok = processes.activate_window_by_pid(delta_force_pid)
                if not ok:
                    logger.error("激活 三角洲行动 窗口失败")
                    logger.info(f"{retry_interval} 秒后重试...")
                    time.sleep(retry_interval)
                    continue
                break
            break
        break
    
    template_login_btn_path = TEMPLATE_DIR / "login_btn.png"
    template_login_btn = vision.image_read(str(template_login_btn_path))
    if template_login_btn is None:
        logger.error(f"未找到 登录按钮模板图片: {template_login_btn_path}")
        return False
    
    while True:
        screen, region, hwnd = _capture_screen(delta_force_pid, retry_interval, warn="无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
        if screen is None or region is None:
            continue
        origin = (region["left"], region["top"])
        btn_found, btn_score, btn_top_left, btn_bottom_right = vision.find_template(screen, template_login_btn, threshold=0.8, origin=origin)
        logger.info(
            f"登录按钮检测: found={btn_found}, score={btn_score:.4f}, "
            f"top_left={btn_top_left}, bottom_right={btn_bottom_right}"
        )
        if not btn_found or btn_top_left is None or btn_bottom_right is None:
            logger.warning("未找到 登录 按钮，重试中...")
            time.sleep(retry_interval)
            continue
        click_x, click_y = vision.box_center(
            btn_top_left,
            btn_bottom_right,
            offset=(0, 0),
        )
        logger.info(f"准备点击登录按钮，绝对坐标=({click_x}, {click_y})")
        input.click(click_x, click_y)
        logger.info("已点击 登录 按钮")
        break
    
    while True:
        screen, region, hwnd = _capture_screen(delta_force_pid, retry_interval, warn="无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
        if screen is None or region is None:
            continue
        origin = (region["left"], region["top"])
        confirm_found, confirm_score, top_left, bottom_right = vision.find_template(screen, TEMPLATE_CONFIRM_BTN, threshold=0.8, origin=origin)
        logger.info(
            f"登录确认检测: found={confirm_found}, score={confirm_score:.4f}"
        )
        sg_found, sg_score, _, _ = vision.find_template(screen, TEMPLATE_START_GAME, threshold=0.7, origin=origin)
        
        if confirm_found:
            logger.info("检测到登录确认，准备点击确认按钮")
            time.sleep(0.5)
            click_x, click_y = vision.box_center(top_left, bottom_right, offset=(0, 0))
            input.click(click_x, click_y)
            break
        if sg_found:
            logger.info("检测到已进入游戏界面，登录成功")
            break
    
    return True

def quit_account() -> bool:
    """
    退出当前账号，回到登录界面
    """
    delta_force = available_delta_force_window()
    delta_force_pid = delta_force["pid"]
    
    # load template
    TEMPLATE_USR_INFO = load_template("usr_info.png")
    TEMPLATE_LOGOUT = load_template("logout.png")
    TEMPLATE_QUIT_SURE = load_template("quit_sure.png")
    
    retry_count = 0
    max_retry = 20
    
    for _ in range(max_retry):
        screen, region, hwnd = capture.window_by_pid(delta_force_pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template_edge(
            screen,
            TEMPLATE_USR_INFO,
            threshold=0.68,
            origin=origin,
            blur_ksize=3,
            canny_low=60,
            canny_high=140,
        )
        logger.info(
            f"用户信息检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if not found or top_left is None or bottom_right is None:
            logger.warning("未检测到用户信息区域，重试中...")
            time.sleep(0.5)
            continue
        click_x, click_y = vision.box_center(
            top_left,
            bottom_right,
            offset=(0, 0),
        )
        logger.info(f"准备点击用户信息区域，绝对坐标=({click_x}, {click_y})")
        time.sleep(0.5)
        input.click(click_x, click_y)
        break
    else:
        logger.error("多次重试未找到用户信息区域，停止退出账户流程")
        return False
    
    while True:
        screen, region, hwnd = capture.window_by_pid(delta_force_pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template_edge(
            screen,
            TEMPLATE_LOGOUT,
            threshold=0.68,
            origin=origin,
            blur_ksize=3,
            canny_low=60,
            canny_high=140,
        )
        logger.info(
            f"退出按钮检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if not found or top_left is None or bottom_right is None:
            logger.warning("未检测到退出按钮，重试中...")
            time.sleep(0.5)
            retry_count += 1
            if retry_count >= max_retry:
                logger.error("多次重试未找到退出按钮，停止退出账户流程")
                return False
            continue
        click_x, click_y = vision.box_center(
            top_left,
            bottom_right,
            offset=(0, 0),
        )
        logger.info(f"准备点击退出按钮，绝对坐标=({click_x}, {click_y})")
        time.sleep(0.5)
        input.click(click_x, click_y)
        logger.info("已点击退出按钮，等待界面切换...")
        break
    
    time.sleep(1)
    screen, region, hwnd = capture.window_by_pid(delta_force_pid)
    if screen is None or region is None:
        logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
        return False
    origin = (region["left"], region["top"])
    found, score, top_left, bottom_right = vision.find_template_edge(
        screen,
        TEMPLATE_QUIT_SURE,
        threshold=0.68,
        origin=origin,
        blur_ksize=3,
        canny_low=60,
        canny_high=140,
    )
    logger.info(
        f"退出确认检测: found={found}, score={score:.4f}, "
        f"top_left={top_left}, bottom_right={bottom_right}"
    )
    if not found or top_left is None or bottom_right is None:
        logger.error("未检测到退出确认按钮，停止退出账户流程")
        return False
    click_x, click_y = vision.box_center(
        top_left,
        bottom_right,
        offset=(0, 0),
    )
    logger.info(f"准备点击退出确认按钮，绝对坐标=({click_x}, {click_y})")
    time.sleep(0.5)
    input.click(click_x, click_y)
    logger.info("已点击退出确认按钮")
    return True

def open_game() -> bool:
    """
    点击开始游戏按钮，进入游戏
    """
    delta_force = available_delta_force_window()
    delta_force_pid = delta_force["pid"]
    
    TEMPLATE_START_GAME = load_template("start_game.png")
    TEMPLATE_SHOUQUAN = load_template("shouquan.png")
    
    while True:
        while True:
            screen, region, hwnd = capture.window_by_pid(delta_force_pid)
            if screen is None or region is None:
                logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
                continue
            origin = (region["left"], region["top"])
            found, score, top_left, bottom_right = vision.find_template(
                screen,
                TEMPLATE_START_GAME,
                threshold=0.8,
                origin=origin,
            )
            logger.info(
                f"开始游戏按钮检测: found={found}, score={score:.4f}, "
                f"top_left={top_left}, bottom_right={bottom_right}"
            )
            if not found or top_left is None or bottom_right is None:
                logger.warning("未检测到 开始游戏 按钮，重试中...")
                time.sleep(0.5)
                continue
            click_x, click_y = vision.box_center(top_left, bottom_right)
            logger.info(f"准备点击 开始游戏 按钮，绝对坐标=({click_x}, {click_y})")
            time.sleep(0.5)
            input.click(click_x, click_y)
            logger.info("已点击 开始游戏 按钮")
            break

        time.sleep(2)
        for _ in range(10):
            screen, region, hwnd = capture.window_by_pid(delta_force_pid)
            if screen is None or region is None:
                time.sleep(0.5)
                continue
            origin = (region["left"], region["top"])
            found, score, top_left, bottom_right = vision.find_template(
                screen,
                TEMPLATE_SHOUQUAN,
                threshold=0.8,
                origin=origin,
            )
            logger.info(
                f"授权界面检测: found={found}, score={score:.4f}, "
                f"top_left={top_left}, bottom_right={bottom_right}"
            )
            if found and top_left is not None and bottom_right is not None:
                input.click(*vision.box_center(top_left, bottom_right))
                logger.info("检测到授权界面，已点击授权按钮，准备重新开始游戏")
                time.sleep(1)
                break
            time.sleep(0.5)
        else:
            return True
        

def check_start() -> Optional[int]:
    """
    检查是否已进入游戏界面
    """
    global client_pid
    if client_pid is not None:
        logger.info(f"已知 client_pid={client_pid}，尝试激活对应窗口以确认游戏界面是否可用...")
        ok = processes.activate_window_by_pid(client_pid)
        if ok:
            logger.info("已激活 三角洲行动 客户端 窗口，确认游戏界面可用")
            return client_pid
        else:
            logger.warning("通过已知 client_pid 激活窗口失败，可能进程已重启，重置 client_pid 并继续查找")
            client_pid = None
    while True:
        game_client = find_best_delta_force_client_process()
        if not game_client:
            logger.error("未找到 三角洲行动 客户端 相关进程，无法确认是否进入游戏")
            continue
        game_client_pid = game_client["pid"]
        client_pid = game_client_pid
        break
    return game_client_pid

def start_game() -> bool:
    """打开游戏到主页面"""
    pid = check_start()
    activate_delta_force_client(pid)
    
    TEMPLATE_FENGHUO1 = load_template("fenghuo1.png")
    TEMPLATE_FENGHUO2 = load_template("fenghuo2.png")
    TEMPLATE_FENGHUO_HOVERED = load_template("fenghuo_hovered.png")
    TEMPLATE_JOIN_GAME = load_template("join_game.png")
    TEMPLATE_CONTINUE = load_template("continue.png")
    TEMPLATE_TAB_CONTINUE = load_template("tab_continue.png")
    
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            TEMPLATE_FENGHUO1,
            threshold=0.75,
            origin=origin
        )
        feng2_found, feng2_score, feng2_top_left, feng2_bottom_right = vision.find_template(
            screen,
            TEMPLATE_FENGHUO2,
            threshold=0.75,
            origin=origin
        )
        hovered_found, hovered_score, hovered_top_left, hovered_bottom_right = vision.find_template(
            screen,
            TEMPLATE_FENGHUO_HOVERED,
            threshold=0.8,
            origin=origin,
        )
        
        logger.info(
            f"主页面检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if found:
            logger.info("检测到烽火主页面，准备点击")
            click_x, click_y = vision.box_center(
                top_left,
                bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击主页面，绝对坐标=({click_x}, {click_y})")
            time.sleep(0.5)
            input.click(click_x, click_y)
            break
        if feng2_found:
            logger.info("检测到烽火主页面2，准备点击")
            click_x, click_y = vision.box_center(
                feng2_top_left,
                feng2_bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击主页面2，绝对坐标=({click_x}, {click_y})")
            time.sleep(0.5)
            input.click(click_x, click_y)
            break
        if hovered_found:
            logger.info(f"检测到高亮烽火卡片，score={hovered_score:.4f}，准备点击")
            input.click(*vision.box_center(hovered_top_left, hovered_bottom_right))
            break
        time.sleep(0.5)
    time.sleep(2)
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            TEMPLATE_JOIN_GAME,
            threshold=0.8,
            origin=origin,
        )
        cfound, cscore, c_top_left, c_bottom_right = vision.find_template(
            screen,
            TEMPLATE_CONTINUE,
            threshold=0.7,
            origin=origin,
        )
        
        logger.info(
            f"进入游戏检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        logger.info(
            f"继续按钮检测: found={cfound}, score={cscore:.4f}, "
            f"top_left={c_top_left}, bottom_right={c_bottom_right}"
        )
        
        if found and top_left is not None and bottom_right is not None:
            logger.info("检测到进入游戏按钮，准备点击")
            click_x, click_y = vision.box_center(
                top_left,
                bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击进入游戏按钮，绝对坐标=({click_x}, {click_y})")
            time.sleep(0.5)
            input.click(click_x, click_y)
            continue
        elif cfound and c_top_left is not None and c_bottom_right is not None:
            logger.info("检测到继续按钮，准备点击继续")
            input.hotkey("space")
            break
        else:
            logger.info("未检测到进入游戏或继续按钮，继续等待...")
            time.sleep(1.0)
    
    time.sleep(3)
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            activate_delta_force_client(pid)
            continue
        
        origin = (region["left"], region["top"])
        tab_found, tab_score, tab_top_left, tab_bottom_right = vision.find_template(
            screen,
            TEMPLATE_TAB_CONTINUE,
            threshold=0.8,
            origin=origin,
        )
        if tab_found and tab_top_left is not None and tab_bottom_right is not None:
            logger.info("检测到特勤处")
            time.sleep(1)
            input.hotkey("tab")
            break
        time.sleep(0.5)
    return True
        
def open_teqingchu() -> bool:
    """打开特勤处"""
    pid = check_start()
    activate_delta_force_client(pid)
    
    TEMPLATE_TEQINGCHU = load_template("teqingchu.png")
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            TEMPLATE_TEQINGCHU,
            threshold=0.65,
            origin=origin,
        )
        logger.info(
            f"特勤处检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if not found or top_left is None or bottom_right is None:
            time.sleep(1)
            logger.info("未检测到特勤处，输入E键更换页面")
            input.press("e")
            continue
        break
    return True

def read_info(skipped: frozenset[int] = frozenset()) -> Optional[list[bool]]:
    """读取每个特勤处是否正在制造
    返回:
        [技术中心, 工作台, 制药台, 防具台]
        True  -> 正在制造
        False -> 未在制造（未开始 / 已完成领取后）
    """
    pid = check_start()
    activate_delta_force_client(pid)

    TEMPLATE_TECHNOLOGYCENTER = load_template("technologycenter.png")
    TEMPLATE_WORKBENCH = load_template("workbench.png")
    TEMPLATE_PHARMACEUTICALPLATFORM = load_template("pharmaceuticalplatform.png")
    TEMPLATE_ARMORPLATFORM = load_template("armorplatform.png")

    TEMPLATE_MAKING = load_template("making.png")
    TEMPLATE_STOP = load_template("stop.png")
    TEMPLATE_NOTFOUND = load_template("notfound.png")
    TEMPLATE_GO_MAKE = load_template("go_make.png")
    TEMPLATE_GETDONE = load_template("getdone.png")

    def open_and_check(sleep_time: float = 0.5) -> Optional[bool]:
        """打开制造界面并检查当前状态"""

        # 先进入制造界面
        while True:
            screen, region, hwnd = capture.window_by_pid(pid)
            if screen is None or region is None:
                logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
                return None

            origin = (region["left"], region["top"])

            making_found, making_score, making_top_left, making_bottom_right = vision.find_template(
                screen,
                TEMPLATE_MAKING,
                threshold=0.7,
                origin=origin,
            )

            go_make_found, go_make_score, go_make_top_left, go_make_bottom_right = vision.find_template(
                screen,
                TEMPLATE_GO_MAKE,
                threshold=0.7,
                origin=origin,
            )

            logger.info(
                f"制造入口检测: making_found={making_found}, making_score={making_score:.4f}, "
                f"go_make_found={go_make_found}, go_make_score={go_make_score:.4f}"
            )

            if go_make_found and go_make_top_left is not None and go_make_bottom_right is not None:
                logger.info("检测到未开始制造，准备点击去制造按钮")
                click_x, click_y = vision.box_center(
                    go_make_top_left,
                    go_make_bottom_right,
                    offset=(0, 0),
                )
                logger.info(f"准备点击去制造，绝对坐标=({click_x}, {click_y})")
                input.click(click_x, click_y)
                time.sleep(sleep_time)
                break

            if making_found and making_top_left is not None and making_bottom_right is not None:
                logger.info("检测到制造按钮，准备点击进入制造界面")
                click_x, click_y = vision.box_center(
                    making_top_left,
                    making_bottom_right,
                    offset=(0, 0),
                )
                logger.info(f"准备点击制造，绝对坐标=({click_x}, {click_y})")
                input.click(click_x, click_y)
                time.sleep(sleep_time)
                break

            time.sleep(sleep_time)

        # 等界面稳定
        time.sleep(1.0)

        while True:
            screen, region, hwnd = capture.window_by_pid(pid)
            if screen is None or region is None:
                logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
                return None

            window_origin = (region["left"], region["top"])
            h, w = screen.shape[:2]

            # 右下区域：用于 stop / getdone
            action_x1 = int(w * 0.50)
            action_y1 = int(h * 0.75)
            action_roi = screen[action_y1:h, action_x1:w]
            action_origin = (window_origin[0] + action_x1, window_origin[1] + action_y1)

            # 中间区域：用于 notfound（“请放入生产图纸”）
            center_x1 = int(w * 0.48)
            center_y1 = int(h * 0.35)
            center_x2 = int(w * 0.78)
            center_y2 = int(h * 0.72)
            center_roi = screen[center_y1:center_y2, center_x1:center_x2]
            center_origin = (window_origin[0] + center_x1, window_origin[1] + center_y1)

            stop_found, stop_score, stop_top_left, stop_bottom_right = vision.find_template(
                action_roi,
                TEMPLATE_STOP,
                threshold=0.72,
                origin=action_origin,
            )

            getdone_found, getdone_score, getdone_top_left, getdone_bottom_right = vision.find_template(
                action_roi,
                TEMPLATE_GETDONE,
                threshold=0.72,
                origin=action_origin,
            )

            notfound_found, notfound_score, notfound_top_left, notfound_bottom_right = vision.find_template(
                center_roi,
                TEMPLATE_NOTFOUND,
                threshold=0.60,
                origin=center_origin,
            )

            logger.info(
                f"停止制造检测: found={stop_found}, score={stop_score:.4f}, "
                f"top_left={stop_top_left}, bottom_right={stop_bottom_right}"
            )
            logger.info(
                f"完成制造检测: found={getdone_found}, score={getdone_score:.4f}, "
                f"top_left={getdone_top_left}, bottom_right={getdone_bottom_right}"
            )
            logger.info(
                f"未找到检测: found={notfound_found}, score={notfound_score:.4f}, "
                f"top_left={notfound_top_left}, bottom_right={notfound_bottom_right}"
            )

            # 优先级：
            # 1. 收获
            # 2. 停止
            # 3. 未放入生产图纸
            if getdone_found and getdone_top_left is not None and getdone_bottom_right is not None:
                logger.info("检测到已完成制造，准备点击领取")
                click_x, click_y = vision.box_center(
                    getdone_top_left,
                    getdone_bottom_right,
                    offset=(0, 0),
                )
                logger.info(f"准备点击领取，绝对坐标=({click_x}, {click_y})")
                input.click(click_x, click_y)
                time.sleep(2)
                input.press("space")
                time.sleep(sleep_time)
                input.press("esc")
                time.sleep(sleep_time)
                input.press("esc")
                return False

            if stop_found and stop_top_left is not None and stop_bottom_right is not None:
                logger.info("检测到正在制造")
                time.sleep(sleep_time)
                input.press("esc")
                time.sleep(sleep_time)
                input.press("esc")
                return True

            if notfound_found and notfound_top_left is not None and notfound_bottom_right is not None:
                logger.info("检测到未开始制造（请放入生产图纸）")
                time.sleep(sleep_time)
                input.press("esc")
                time.sleep(sleep_time)
                input.press("esc")
                return False

            logger.warning("未检测到 stop/getdone/notfound，继续重试中...")
            time.sleep(sleep_time)

    platforms = [
        TEMPLATE_TECHNOLOGYCENTER,
        TEMPLATE_WORKBENCH,
        TEMPLATE_PHARMACEUTICALPLATFORM,
        TEMPLATE_ARMORPLATFORM,
    ]
    platform_names = ["技术中心", "工作台", "制药台", "防具台"]

    index = 0
    status = []

    while True:
        if index in skipped:
            logger.info(f"跳过平台状态读取: {platform_names[index]}")
            status.append(True)
            index += 1
            if index >= len(platforms):
                break
            continue

        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            return None

        origin = (region["left"], region["top"])

        found, score, top_left, bottom_right = vision.find_template(
            screen,
            platforms[index],
            threshold=0.8,
            origin=origin,
        )

        logger.info(
            f"平台检测[{platform_names[index]}]: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )

        if found and top_left is not None and bottom_right is not None:
            logger.info(f"检测到特勤处-{platform_names[index]}，点击进入")
            click_x, click_y = vision.box_center(
                top_left,
                bottom_right,
                offset=(0, 0),
            )
            logger.info(f"点击坐标: ({click_x}, {click_y})")
            input.click(click_x, click_y)
            time.sleep(0.5)

            result = open_and_check()
            if result is None:
                return None
            status.append(result)
            index += 1

            if index >= len(platforms):
                break

        time.sleep(0.3)

    return status

def make_object(err: int = 0):
    pid = check_start()
    activate_delta_force_client(pid)

    TEMPLATE_COMPLETE = load_template("complete.png")
    TEMPLATE_PRODUCTION = load_template("production.png")

    def check_production(click: bool = True) -> bool:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            return False

        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            TEMPLATE_PRODUCTION,
            threshold=0.8,
            origin=origin,
        )

        if found and top_left is not None and bottom_right is not None:
            logger.info("检测到材料足够")
            if click:
                click_x, click_y = vision.box_center(
                    top_left,
                    bottom_right,
                    offset=(0, 0),
                )
                logger.info(f"准备点击生产按钮，绝对坐标=({click_x}, {click_y})")
                input.click(click_x, click_y)
            return True

        logger.info("未检测到材料足够，准备补齐")
        return False

    # 已经能生产就直接点生产
    if check_production(click=True):
        return True

    # 先点“补齐”
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            return False

        origin = (region["left"], region["top"])
        complete_found, complete_score, complete_top_left, complete_bottom_right = vision.find_template(
            screen,
            TEMPLATE_COMPLETE,
            threshold=0.8,
            origin=origin,
        )

        if complete_found and complete_top_left is not None and complete_bottom_right is not None:
            click_x, click_y = vision.box_center(
                complete_top_left,
                complete_bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击补齐按钮，绝对坐标=({click_x}, {click_y})")
            input.click(click_x, click_y)
            break

        time.sleep(0.3)

    time.sleep(0.8)

    # 直接写死点击补齐确认按钮（窗口内相对坐标）
    # 你提供的最终坐标：x=963, y=749
    retry_count = 0

    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            return False

        click_x = region["left"] + 963
        click_y = region["top"] + 749

        logger.info(f"准备点击补齐确认按钮（写死坐标），绝对坐标=({click_x}, {click_y})")
        input.click(click_x, click_y)
        time.sleep(1.0)

        # 点击后如果已经能生产，直接点生产并结束
        if check_production(click=True):
            return True

        retry_count += 1
        if retry_count >= 6:
            logger.warning("写死坐标点击补齐确认按钮多次后，仍未检测到生产按钮")
            break

    if err < 3:
        logger.warning("购买后仍未检测到生产按钮，准备重试 make_object")
        return make_object(err + 1)

    logger.error("补齐后仍未检测到材料足够，可能出现异常，停止尝试")
    return False

def find_object(obj_img: np.ndarray, retry_interval: float = 0.5) -> Optional[tuple[int, int]]:
    pid = check_start()
    activate_delta_force_client(pid)
    
    TEMPLATE_JS = load_template("js.png")
    TEMPLATE_PSBAR = load_template("psbar.png")
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        js_found, js_score, js_top_left, js_bottom_right = vision.find_template(
            screen,
            TEMPLATE_JS,
            threshold=0.8,
            origin=origin,
        )
        logger.info(
            f"界面检测: found={js_found}, score={js_score:.4f}, "
            f"top_left={js_top_left}, bottom_right={js_bottom_right}"
        )
        if js_found and js_top_left is not None and js_bottom_right is not None:
            click_x, click_y = vision.box_center(
                js_top_left,
                js_bottom_right,
                offset=(0, 0),
            )
            input.move_to(click_x, click_y)
            break
        
        barfound, barscore, bar_top_left, bar_bottom_right = vision.find_template(
            screen,
            TEMPLATE_PSBAR,
            threshold=0.65,
            origin=origin,
        )
        logger.info(
            f"界面检测2: found={barfound}, score={barscore:.4f}, "
            f"top_left={bar_top_left}, bottom_right={bar_bottom_right}"
        )
        if barfound and bar_top_left is not None and bar_bottom_right is not None:
            click_x, click_y = vision.box_center(
                bar_top_left,
                bar_bottom_right,
                offset=(0, 0),
            )
            input.move_to(click_x, click_y)
            input.scroll(5) # 物品栏向上滚动，尝试显示需要的物品
            time.sleep(retry_interval)
            continue
        input.scroll(5) # 物品栏向上滚动，尝试显示需要的物品
        time.sleep(retry_interval)
    time.sleep(0.5)
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            obj_img,
            threshold=0.8,
            origin=origin,
        )
        logger.info(
            f"物品检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if found and top_left is not None and bottom_right is not None:
            click_x, click_y = vision.box_center(
                top_left,
                bottom_right,
                offset=(0, 0),
            )
            logger.info(f"检测到物品，绝对坐标=({click_x}, {click_y})")
            
            input.click(click_x, click_y)
            return click_x, click_y
        else:
            input.scroll(-1) # 物品栏向下滚动，尝试显示更多物品
            time.sleep(0.5)
            continue
    
def open_object(index: int):
    pid = check_start()
    activate_delta_force_client(pid)
    

    object_index = ["technologycenter", "workbench", "pharmaceuticalplatform", "armorplatform"]
    TEMPLATE = load_template(f"{object_index[index]}.png")
    TEMPLATE_MAKING = load_template("making.png")
    TEMPLATE_GO_MAKE = load_template("go_make.png")
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        
        origin = (region["left"], region["top"])
        
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            TEMPLATE,
            threshold=0.8,
            origin=origin,
        )
        logger.info(
            f"界面检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if found and top_left is not None and bottom_right is not None:
            click_x, click_y = vision.box_center(
                top_left,
                bottom_right,
                offset=(0, 0),
            )
            input.click(click_x, click_y)
            break
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        making_found, making_score, making_top_left, making_bottom_right = vision.find_template(
            screen,
            TEMPLATE_MAKING,
            threshold=0.8,
            origin=origin,
        )
        go_make_found, go_make_score, go_make_top_left, go_make_bottom_right = vision.find_template(
            screen,
            TEMPLATE_GO_MAKE,
            threshold=0.8,
            origin=origin,
        )
    
        logger.info(
            f"制造界面检测: found={making_found}, score={making_score:.4f}, "
            f"top_left={making_top_left}, bottom_right={making_bottom_right}"
        )
        logger.info(
            f"去制造界面检测: found={go_make_found}, score={go_make_score:.4f}, "
            f"top_left={go_make_top_left}, bottom_right={go_make_bottom_right}"
        )
        
        if go_make_found and go_make_top_left is not None and go_make_bottom_right is not None:
            logger.info("检测到去制造界面，准备点击")
            click_x, click_y = vision.box_center(
                go_make_top_left,
                go_make_bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击去制造，绝对坐标=({click_x}, {click_y})")
            input.click(click_x, click_y)
            break
        if making_found and making_top_left is not None and making_bottom_right is not None:
            logger.info("检测到制造界面，准备点击")
            click_x, click_y = vision.box_center(
                making_top_left,
                making_bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击制造，绝对坐标=({click_x}, {click_y})")
            input.click(click_x, click_y)
            break
        time.sleep(0.3)
    return True

def quit_object() -> bool:
    pid = check_start()
    activate_delta_force_client(pid)
    
    input.press("esc") # 退出制造界面
    time.sleep(0.1)
    input.press("esc") # 需要退出两次才能回到特勤处主界面
    return True
    
def quit_game() -> bool:
    pid = check_start()
    activate_delta_force_client(pid)
    
    TEMPLATE_QUIT_GAME = load_template("quit_game.png")
    TEMPLATE_QUEREN = load_template("queren.png")
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        found, score, top_left, bottom_right = vision.find_template(
            screen,
            TEMPLATE_QUIT_GAME,
            threshold=0.8,
            origin=origin,
        )
        logger.info(
            f"退出游戏检测: found={found}, score={score:.4f}, "
            f"top_left={top_left}, bottom_right={bottom_right}"
        )
        if found and top_left is not None and bottom_right is not None:
            click_x, click_y = vision.box_center(
                top_left,
                bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击退出游戏按钮，绝对坐标=({click_x}, {click_y})")
            input.click(click_x, click_y)
            break
        
        input.press("esc") # 先按一次esc尝试打开退出游戏界面
        time.sleep(0.3)
    
    while True:
        screen, region, hwnd = capture.window_by_pid(pid)
        if screen is None or region is None:
            logger.error("无法截取 三角洲行动 窗口，可能窗口未完全加载或被遮挡")
            continue
        origin = (region["left"], region["top"])
        quereng_found, quereng_score, quereng_top_left, quereng_bottom_right = vision.find_template(
            screen,
            TEMPLATE_QUEREN,
            threshold=0.8,
            origin=origin,
        )
        logger.info(
            f"确认退出检测: found={quereng_found}, score={quereng_score:.4f}, "
            f"top_left={quereng_top_left}, bottom_right={quereng_bottom_right}"
        )
        if quereng_found and quereng_top_left is not None and quereng_bottom_right is not None:
            click_x, click_y = vision.box_center(
                quereng_top_left,
                quereng_bottom_right,
                offset=(0, 0),
            )
            logger.info(f"准备点击确认退出按钮，绝对坐标=({click_x}, {click_y})")
            input.click(click_x, click_y)
            break
        time.sleep(0.3)
    return True
