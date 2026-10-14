import os
import cv2
import numpy as np


# =========================
# 配置
# =========================
SCREEN_PATH = r"data\test\screen.png"
TEMPLATE_PATH = r"data\test\template.png"
OUTPUT_DIR = r"data\test\debug_output"

WHITE_THRESHOLD = 200
CANNY_LOW = 80
CANNY_HIGH = 160


# =========================
# 工具函数
# =========================
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def image_read(path: str) -> np.ndarray | None:
    """
    兼容中文路径读取图片
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
        if data.size == 0:
            return None
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def save_image(path: str, image: np.ndarray) -> None:
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, image)
    if ok:
        buf.tofile(path)


def prepare_white_mask(image: np.ndarray, threshold: int = 200) -> np.ndarray:
    """
    灰度 + 二值化，尽量提取偏白色图标
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    # 去小噪点
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return gray, binary


def prepare_edge_image(image: np.ndarray, canny_low: int = 80, canny_high: int = 160) -> np.ndarray:
    """
    边缘图
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, canny_low, canny_high)
    return gray, edges


def find_template(processed_screen: np.ndarray, processed_template: np.ndarray):
    """
    返回最佳匹配信息
    """
    sh, sw = processed_screen.shape[:2]
    th, tw = processed_template.shape[:2]

    if tw > sw or th > sh:
        return False, -1.0, None, None

    result = cv2.matchTemplate(processed_screen, processed_template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    top_left = max_loc
    bottom_right = (top_left[0] + tw, top_left[1] + th)
    return True, float(max_val), top_left, bottom_right


def draw_match_box(image: np.ndarray, top_left, bottom_right, label: str = "") -> np.ndarray:
    out = image.copy()
    cv2.rectangle(out, top_left, bottom_right, (0, 255, 0), 2)

    if label:
        cv2.putText(
            out,
            label,
            (top_left[0], max(20, top_left[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    return out


# =========================
# 主流程
# =========================
def main():
    ensure_dir(OUTPUT_DIR)

    screen = image_read(SCREEN_PATH)
    template = image_read(TEMPLATE_PATH)

    if screen is None:
        print(f"读取 screen 失败: {SCREEN_PATH}")
        return
    if template is None:
        print(f"读取 template 失败: {TEMPLATE_PATH}")
        return

    print("screen shape:", screen.shape)
    print("template shape:", template.shape)

    # 保存原图
    save_image(os.path.join(OUTPUT_DIR, "01_screen.png"), screen)
    save_image(os.path.join(OUTPUT_DIR, "02_template.png"), template)

    # -------------------------
    # 1. 灰度 + 二值化白色区域
    # -------------------------
    white_screen_gray, white_screen_bin = prepare_white_mask(screen, threshold=WHITE_THRESHOLD)
    white_template_gray, white_template_bin = prepare_white_mask(template, threshold=WHITE_THRESHOLD)

    save_image(os.path.join(OUTPUT_DIR, "11_white_screen_gray.png"), white_screen_gray)
    save_image(os.path.join(OUTPUT_DIR, "12_white_screen_binary.png"), white_screen_bin)
    save_image(os.path.join(OUTPUT_DIR, "13_white_template_gray.png"), white_template_gray)
    save_image(os.path.join(OUTPUT_DIR, "14_white_template_binary.png"), white_template_bin)

    ok_white, white_score, white_top_left, white_bottom_right = find_template(
        white_screen_bin,
        white_template_bin,
    )

    print(f"[WHITE] score = {white_score:.4f}, top_left = {white_top_left}, bottom_right = {white_bottom_right}")

    if ok_white:
        white_result = draw_match_box(
            screen,
            white_top_left,
            white_bottom_right,
            label=f"WHITE {white_score:.4f}",
        )
        save_image(os.path.join(OUTPUT_DIR, "15_white_match_result.png"), white_result)

    # -------------------------
    # 2. 边缘图匹配
    # -------------------------
    edge_screen_gray, edge_screen = prepare_edge_image(screen, canny_low=CANNY_LOW, canny_high=CANNY_HIGH)
    edge_template_gray, edge_template = prepare_edge_image(template, canny_low=CANNY_LOW, canny_high=CANNY_HIGH)

    save_image(os.path.join(OUTPUT_DIR, "21_edge_screen_gray.png"), edge_screen_gray)
    save_image(os.path.join(OUTPUT_DIR, "22_edge_screen.png"), edge_screen)
    save_image(os.path.join(OUTPUT_DIR, "23_edge_template_gray.png"), edge_template_gray)
    save_image(os.path.join(OUTPUT_DIR, "24_edge_template.png"), edge_template)

    ok_edge, edge_score, edge_top_left, edge_bottom_right = find_template(
        edge_screen,
        edge_template,
    )

    print(f"[EDGE]  score = {edge_score:.4f}, top_left = {edge_top_left}, bottom_right = {edge_bottom_right}")

    if ok_edge:
        edge_result = draw_match_box(
            screen,
            edge_top_left,
            edge_bottom_right,
            label=f"EDGE {edge_score:.4f}",
        )
        save_image(os.path.join(OUTPUT_DIR, "25_edge_match_result.png"), edge_result)

    # -------------------------
    # 对比结论
    # -------------------------
    print()
    if white_score > edge_score:
        print("当前测试结果：白色区域二值匹配分数更高")
    elif edge_score > white_score:
        print("当前测试结果：边缘匹配分数更高")
    else:
        print("当前测试结果：两者分数相同")

    print(f"所有效果图已保存到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()