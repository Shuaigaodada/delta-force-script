# delta-force-script

三角洲行动（Delta Force）PC 端「特勤处制造」批量自动化脚本：按 QQ 账号逐个登录游戏、进入特勤处、检查四个制造位并按需开始制造，全部在终端（TUI）中操作。

## 简介

本项目通过窗口截图 + OpenCV 模板匹配 + Tesseract OCR + 模拟键鼠输入驱动游戏客户端，适用于需要给多个账号补制造/收菜的重复操作场景。核心流程写在 `src/core/workflow.py`，入口在 `launcher.py` 与 `src/main.py`。

主要能力：

- 读取 `data/accounts.json` 中的 QQ 账号列表，支持在菜单里增删账号。
- 逐个账号执行：登录账号 → 打开游戏 → 开始游戏 → 打开特勤处 → 读取四个制造位状态 → 对空闲制造位查找目标物品并开始制造 → 退出游戏 → 退出账号。
- 运行前可勾选本次要执行/跳过的制造位（技术中心、工作台、制药台、防具台）。
- 任一关键步骤失败即停止该账号的后续流程，并在日志中记录原因；账号之间互不影响。
- 自动以管理员权限重新启动自身（Windows UAC），并统一把崩溃堆栈写入 `logs/crash.log`。

## 目录结构

```
delta-force-script/
├─ launcher.py                  # 启动入口：切工作目录、建 logs/、调用 src.main.main()
├─ src/
│  ├─ main.py                   # TUI 主流程：管理员检查、账号菜单、制造位选择、逐账号执行
│  ├─ core/
│  │  ├─ capture.py             # mss 全屏截图
│  │  ├─ input.py               # PyDirectInput / 剪贴板等输入封装
│  │  ├─ processes.py           # 查找并激活三角洲客户端进程/窗口
│  │  ├─ vision.py              # 模板匹配、OCR（pytesseract）等图像识别
│  │  └─ workflow.py            # 登录、开游戏、特勤处、读取制造位、制造等业务步骤
│  └─ utils/
│     ├─ admin.py               # 管理员权限判断与 UAC 提权重启
│     ├─ loggers.py             # colorlog 彩色控制台日志
│     └─ paths.py               # data/、custom/、llibs/ 等路径解析（兼容 PyInstaller）
├─ data/
│  ├─ accounts.json             # 运行账号列表（字符串数组）
│  └─ templates/delta_force/    # 界面模板图；custom/1-4.png 为各制造位的目标物品模板
├─ llibs/tesseract-ocr/         # 内置 Tesseract OCR 发行版（tesseract.exe、tessdata 等）
├─ scripts/
│  ├─ start-prepared-env.ps1    # 校验依赖后启动（推荐入口）
│  └─ check-environment.py      # 校验 venv 路径与 requirements.txt 钉死版本
├─ tests/                       # unittest 与手工调试脚本
├─ delta-force-script.spec      # PyInstaller 打包配置（uac_admin=True、console=True）
├─ requirements.txt             # UTF-16 编码的钉版本依赖清单
└─ TODO.txt                     # 后续计划（自动收菜、账号切换、自动出售等）
```

## 环境要求

- Windows 10/11（依赖 `msvcrt`、`pywin32`、`PyDirectInput`、`mss`，仅支持 Windows）。
- Python 3.10（仓库内 `venv/` 由 Python 3.10.3 创建）。
- 已安装三角洲行动 PC 客户端，并能正常登录游戏。
- 运行需要管理员权限（脚本会自行请求 UAC 提权）。
- 虚拟环境必须放在项目根目录下、且目录名严格为 `venv`：`scripts/check-environment.py` 会校验 `sys.prefix` 是否等于 `<项目根>/venv`，否则直接拒绝启动。

## 启动方式（Windows PowerShell）

首次准备环境：

```powershell
cd E:\Projects\delta-force-script
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动（推荐，先校验钉版本依赖，再运行 `launcher.py`）：

```powershell
cd E:\Projects\delta-force-script
.\scripts\start-prepared-env.ps1
```

只校验环境、不启动程序：

```powershell
.\scripts\start-prepared-env.ps1 -CheckEnvironmentOnly
```

手动启动（跳过依赖校验）：

```powershell
.\venv\Scripts\python.exe -B .\launcher.py
```

注意：

- 非管理员运行时，程序会通过 `ShellExecuteW` 以 `runas` 重新拉起自身，旧进程退出；请在 UAC 弹窗中允许。
- `requirements.txt` 由 `check-environment.py` 按 UTF-16/UTF-8 自动识别编码，请保持「每行一个 `包==版本`」格式，否则脚本会拒绝校验。
- 缺少或版本不一致的依赖会以退出码 2 阻断启动，并打印缺失/不匹配清单。

## 使用方法

1. 启动后进入账号菜单（`W/S/A/D` 或 `↑/↓` 移动，`Enter` 确认，`Esc` 返回）：
   - `开始运行`：使用当前账号列表开始自动化；
   - `添加账号`：输入纯数字 QQ 账号，回车保存到 `data/accounts.json`；
   - `删除账号`：选择账号并二次确认后删除；
   - `退出`：结束程序。
2. 选择本次要执行的制造位：`空格` 勾选/取消，`Enter` 确认，`Esc` 全部执行。
3. 程序按账号顺序自动执行完整流程，过程中请保持游戏窗口可用、不要人工抢占鼠标键盘；需要中断时按 `Ctrl+C`。
4. 将各制造位要制造的目标物品界面截图（只截物品区域）分别保存为
   `data/templates/delta_force/custom/1.png` ~ `4.png`，与制造位一一对应。
5. 日志输出到控制台（带颜色），未捕获异常会追加写入 `logs/crash.log`。

## 已知限制

- 仅支持三角洲行动 PC 客户端与特勤处制造界面；游戏 UI、分辨率或窗口状态变化会导致模板匹配/OCR 失效，需要更新 `data/templates/delta_force/` 下的模板图。
- 无头/最小化窗口不可用：截图取自主屏，运行期间需要保持游戏窗口可见。
- 账号为顺序执行，单账号流程中任一步失败就停止该账号后续步骤（不会重试或跳过）。
- OCR 依赖仓库内 `llibs/tesseract-ocr`（`src/core/vision.py` 会优先使用其中的 `tesseract.exe` 与 `tessdata`）；按本地 Git 规则 `llibs/tesseract-ocr/libtesseract-5.dll` 被 `.gitignore` 排除，新克隆的仓库可能需要自行补齐该运行库。
- `venv/`、`.venv-prepared-*/`、`logs/` 均不入库；换机器必须重新创建 `venv` 并安装钉版本依赖。
- `tests/` 中除 `test_main.py` 等 unittest 外还有手工调试脚本（如鼠标坐标查看器 `test.py`），不会自动运行；自动化测试只覆盖菜单、账号增删、步骤失败即停止等纯逻辑部分。
- `TODO.txt` 中的自动收菜、账号切换、自动出售、邮件领取、哈弗币监控等均尚未实现。

## 许可

MIT，详见 [LICENSE](LICENSE)。
