import time
import json
from src.utils import admin
from src.utils.loggers import logger
from src.core import workflow
from src.utils.paths import custom_path, data_path

ACCOUNTS = []

custom_path().mkdir(parents=True, exist_ok=True)

def load_accounts() -> None:
    global ACCOUNTS
    account_path = data_path("accounts.json")   # 这里顺手统一文件名
    if not account_path.exists():
        logger.warning(f"账户文件 {account_path} 不存在，请创建并添加账户信息")
        return
    try:
        with account_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                ACCOUNTS = list(data.keys())
            elif isinstance(data, list):
                ACCOUNTS = [str(x) for x in data]
            else:
                logger.error(f"账户文件格式不支持: {account_path}")
    except Exception as e:
        logger.error(f"加载账户文件 {account_path} 失败: {e}")

def _workflow(usr_id: str, s: float = 0.3) -> None:
    workflow.login_account(usr_id)
    time.sleep(s)
    workflow.open_game()
    time.sleep(s)
    workflow.start_game()
    time.sleep(s)
    workflow.open_teqingchu()
    time.sleep(s)
    info = workflow.read_info()
    print(info)

    imgs = [workflow.load_template(str(custom_path(f"{i}.png"))) for i in range(1, 5)]
    for index, status in enumerate(info):
        if not status:
            workflow.open_object(index)
            time.sleep(s)
            workflow.find_object(imgs[index])
            time.sleep(s)
            workflow.make_object()
            time.sleep(s)
            workflow.quit_object()
            time.sleep(s)

    workflow.quit_game()
    time.sleep(1)
    workflow.quit_account()

def main() -> None:
    if not admin.ensure_admin_or_relaunch_launcher():   
        logger.error("无法以管理员权限启动 launcher.py，尝试使用管理员权限运行本程序")
        return

    logger.info("当前已是管理员权限，继续执行程序...")
    
    logger.info("正在加载账户信息...")
    load_accounts()
    logger.info(f"共加载到 {len(ACCOUNTS)} 个账户")
    
    for usr_id in ACCOUNTS:
        logger.info(f"正在处理账户: {usr_id}")
        try:
            _workflow(usr_id)
        except Exception as e:
            logger.error(f"账户 {usr_id} 处理失败: {e}")

