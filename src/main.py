import time
import json
import msvcrt
import sys
import traceback
from pathlib import Path

from src.utils import admin
from src.utils.loggers import logger
from src.core import workflow
from src.utils.paths import custom_path, data_path

ACCOUNTS = []
PLATFORM_NAMES = ("技术中心", "工作台", "制药台", "防具台")

custom_path().mkdir(parents=True, exist_ok=True)


def install_global_exception_hook() -> None:
    """
    捕获未被 try/except 接住的异常。
    打包成 exe 后也能在日志里看到具体文件、行号、调用链。
    """

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "程序发生未捕获异常：",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception


def load_accounts() -> None:
    global ACCOUNTS
    ACCOUNTS = []

    account_path = data_path("accounts.json")

    if not account_path.exists():
        logger.warning(f"账户文件 {account_path} 不存在，请创建并添加账户信息")
        return

    try:
        logger.info(f"正在读取账户文件: {account_path}")

        with account_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"账户文件原始类型: {type(data).__name__}")

        if isinstance(data, dict):
            ACCOUNTS = list(data.keys())
        elif isinstance(data, list):
            ACCOUNTS = [str(x) for x in data]
        else:
            logger.error(f"账户文件格式不支持: {account_path}, 实际类型: {type(data).__name__}")

    except Exception:
        logger.exception(f"加载账户文件失败: {account_path}")


def _require_success(step: str, result) -> None:
    if not result:
        raise RuntimeError(f"{step}失败，已停止当前账户流程")


def _read_menu_key() -> str:
    key = msvcrt.getwch()
    if key in ("\x00", "\xe0"):
        return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
    return {
        "w": "up", "a": "up", "s": "down", "d": "down",
        " ": "toggle", "\r": "confirm", "\n": "confirm", "\x1b": "cancel",
    }.get(key.lower(), "")


def _select_menu(title: str, options, read_key=_read_menu_key) -> int | None:
    cursor = 0
    while True:
        print("\033[2J\033[H", end="")
        print(f"{title}\n")
        print("W/S/A/D 或 ↑/↓ 移动，Enter 确认，Esc 返回\n")
        for index, option in enumerate(options):
            marker = ">" if index == cursor else " "
            print(f"{marker} {option}")

        key = read_key()
        if key == "up":
            cursor = (cursor - 1) % len(options)
        elif key == "down":
            cursor = (cursor + 1) % len(options)
        elif key == "confirm":
            return cursor
        elif key == "cancel":
            return None


def save_accounts() -> None:
    account_path = data_path("accounts.json")
    account_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = account_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(ACCOUNTS, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(account_path)


def add_account(input_fn=input) -> bool:
    message = ""
    while True:
        print("\033[2J\033[H", end="")
        if message:
            print(message)
        account = input_fn("输入要添加的 QQ 账号（直接回车取消）：").strip()
        if not account:
            return False
        if not account.isdigit():
            message = "账号只能包含数字。"
            continue
        if account in ACCOUNTS:
            message = "该账号已经存在。"
            continue
        ACCOUNTS.append(account)
        save_accounts()
        return True


def delete_account(read_key=_read_menu_key) -> bool:
    if not ACCOUNTS:
        return False
    selected = _select_menu("选择要删除的账号", ACCOUNTS, read_key)
    if selected is None:
        return False
    confirmed = _select_menu(
        f"确认删除账号 {ACCOUNTS[selected]}？",
        ("取消", "删除"),
        read_key,
    )
    if confirmed != 1:
        return False
    del ACCOUNTS[selected]
    save_accounts()
    return True


def account_menu(read_key=_read_menu_key, input_fn=input) -> bool:
    while True:
        account_list = "、".join(ACCOUNTS) or "无"
        selected = _select_menu(
            f"账号：{account_list}\n\n请选择操作",
            ("开始运行", "添加账号", "删除账号", "退出"),
            read_key,
        )
        if selected is None or selected == 3:
            return False
        if selected == 0:
            if ACCOUNTS:
                return True
            add_account(input_fn)
        elif selected == 1:
            add_account(input_fn)
        elif selected == 2:
            delete_account(read_key)


def choose_skipped_platforms(read_key=_read_menu_key) -> frozenset[int]:
    """使用键盘选择本次运行要跳过的制造位。"""
    cursor = 0
    enabled = set(range(len(PLATFORM_NAMES)))
    while True:
        print("\033[2J\033[H", end="")
        print("选择本次要执行的制造位")
        print("W/S/A/D 或 ↑/↓ 移动，空格勾选/取消，Enter 确认，Esc 全部执行\n")
        for index, name in enumerate(PLATFORM_NAMES):
            marker = ">" if index == cursor else " "
            checked = "x" if index in enabled else " "
            print(f"{marker} [{checked}] {name}")

        key = read_key()
        if key == "up":
            cursor = (cursor - 1) % len(PLATFORM_NAMES)
        elif key == "down":
            cursor = (cursor + 1) % len(PLATFORM_NAMES)
        elif key == "toggle":
            enabled.symmetric_difference_update({cursor})
        elif key == "confirm":
            break
        elif key == "cancel":
            enabled = set(range(len(PLATFORM_NAMES)))
            break

    skipped = frozenset(set(range(len(PLATFORM_NAMES))) - enabled)
    print("本次跳过：" + ("、".join(PLATFORM_NAMES[index] for index in sorted(skipped)) or "无"))
    return skipped


def _workflow(usr_id: str, s: float = 0.3, skipped: frozenset[int] = frozenset()) -> None:
    logger.info(f"[{usr_id}] 开始登录账户")
    _require_success("登录账户", workflow.login_account(usr_id))
    time.sleep(s)

    logger.info(f"[{usr_id}] 打开游戏")
    _require_success("打开游戏", workflow.open_game())
    time.sleep(s)

    logger.info(f"[{usr_id}] 开始游戏")
    _require_success("开始游戏", workflow.start_game())
    time.sleep(s)

    logger.info(f"[{usr_id}] 打开特勤处")
    _require_success("打开特勤处", workflow.open_teqingchu())
    time.sleep(s)

    logger.info(f"[{usr_id}] 读取制造信息")
    info = workflow.read_info(skipped)
    logger.info(f"[{usr_id}] read_info 返回值: {info}, 类型: {type(info).__name__}")

    if info is None:
        raise RuntimeError(f"[{usr_id}] workflow.read_info() 返回 None，后续无法遍历制造状态")

    if not isinstance(info, (list, tuple)):
        raise RuntimeError(f"[{usr_id}] workflow.read_info() 返回类型错误: {type(info).__name__}, 值: {info}")

    logger.info(f"[{usr_id}] 加载模板图片")
    imgs = []

    for index, i in enumerate(range(1, 5)):
        if index in skipped:
            imgs.append(None)
            continue
        img_path = custom_path(f"{i}.png")
        logger.info(f"[{usr_id}] 加载模板: {img_path}")

        img = workflow.load_template(str(img_path))

        if img is None:
            raise RuntimeError(f"[{usr_id}] 模板加载失败，返回 None: {img_path}")

        imgs.append(img)

    for index, status in enumerate(info):
        logger.info(f"[{usr_id}] 当前制造位 index={index}, status={status}")

        if index in skipped:
            logger.info(f"[{usr_id}] 已跳过制造位: {PLATFORM_NAMES[index]}")
            continue

        if index >= len(imgs):
            raise RuntimeError(
                f"[{usr_id}] info 数量超过模板数量: index={index}, imgs数量={len(imgs)}, info={info}"
            )

        if not status:
            logger.info(f"[{usr_id}] 打开制造位: {index}")
            _require_success("打开制造位", workflow.open_object(index))
            time.sleep(s)

            logger.info(f"[{usr_id}] 查找物品: index={index}")
            _require_success("查找物品", workflow.find_object(imgs[index]))
            time.sleep(s)

            logger.info(f"[{usr_id}] 开始制造: index={index}")
            _require_success("开始制造", workflow.make_object())
            time.sleep(s)

            logger.info(f"[{usr_id}] 退出制造位: index={index}")
            workflow.quit_object()
            time.sleep(s)

    logger.info(f"[{usr_id}] 退出游戏")
    _require_success("退出游戏", workflow.quit_game())
    time.sleep(1)

    logger.info(f"[{usr_id}] 退出账户")
    _require_success("退出账户", workflow.quit_account())

    logger.info(f"[{usr_id}] 账户处理完成")


def main() -> None:
    install_global_exception_hook()

    try:
        if not admin.ensure_admin_or_relaunch_launcher():
            logger.error("无法以管理员权限启动 launcher.py，请尝试手动使用管理员权限运行本程序")
            return

        logger.info("当前已是管理员权限，继续执行程序...")

        logger.info("正在加载账户信息...")
        load_accounts()
        logger.info(f"共加载到 {len(ACCOUNTS)} 个账户")

        if sys.stdin.isatty():
            if not account_menu():
                return
        elif not ACCOUNTS:
            logger.warning("没有加载到账户，程序结束")
            return

        skipped = choose_skipped_platforms() if sys.stdin.isatty() else frozenset()

        for usr_id in ACCOUNTS:
            logger.info("=" * 60)
            logger.info(f"正在处理账户: {usr_id}")

            try:
                _workflow(usr_id, skipped=skipped)
            except Exception:
                logger.exception(f"账户 {usr_id} 处理失败，完整错误如下：")

    except Exception:
        logger.exception("main() 发生严重错误，完整错误如下：")


if __name__ == "__main__":
    main()
