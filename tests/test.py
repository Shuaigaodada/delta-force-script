import time
import os
import msvcrt
import pyautogui

def clear():
    os.system("cls")

def main():
    pyautogui.FAILSAFE = False
    saved_points = []

    print("鼠标坐标查看器已启动")
    print("按 [空格] 记录当前坐标")
    print("按 [Q] 退出")
    print()

    try:
        while True:
            x, y = pyautogui.position()

            clear()
            print("鼠标坐标查看器已启动")
            print("按 [空格] 记录当前坐标")
            print("按 [Q] 退出")
            print()
            print(f"当前鼠标坐标: x={x}, y={y}")
            print()

            if saved_points:
                print("已记录坐标:")
                for i, (sx, sy) in enumerate(saved_points, start=1):
                    print(f"{i}. x={sx}, y={sy}")
            else:
                print("已记录坐标: 无")

            if msvcrt.kbhit():
                key = msvcrt.getch()

                if key == b' ':
                    saved_points.append((x, y))
                elif key in (b'q', b'Q'):
                    break

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass

    clear()
    print("程序已退出")
    if saved_points:
        print("最终记录的坐标:")
        for i, (sx, sy) in enumerate(saved_points, start=1):
            print(f"{i}. x={sx}, y={sy}")
    else:
        print("没有记录任何坐标")

if __name__ == "__main__":
    main()