from __future__ import annotations
from typing import Optional
import cv2
import numpy as np
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"D:\programing\delta-force-script\llibs\tesseract-ocr\tesseract.exe"

def image_read(path: str) -> Optional[np.ndarray]:
    """
    从文件读取图像，返回 BGR 格式的 numpy 数组
    """
    img = cv2.imread(path)
    if img is None:
        return None
    return img


def find_template(
    screen: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    origin: tuple[int, int] = (0, 0),
) -> tuple[bool, float, Optional[tuple[int, int]], Optional[tuple[int, int]]]:
    """
    模板匹配。
    返回的 top_left / bottom_right 默认是屏幕绝对坐标：
    - 如果 screen 是整屏截图，origin 用默认 (0, 0)
    - 如果 screen 是窗口截图，origin 传窗口左上角屏幕坐标
    """
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        h, w = template.shape[:2]
        top_left = (max_loc[0] + origin[0], max_loc[1] + origin[1])
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return True, float(max_val), top_left, bottom_right

    return False, float(max_val), None, None


def find_template_multi_scale(
    screen: np.ndarray,
    template: np.ndarray,
    scales: list[float],
    threshold: float = 0.8,
    origin: tuple[int, int] = (0, 0),
) -> tuple[bool, float, Optional[tuple[int, int]], Optional[tuple[int, int]], Optional[float]]:
    """
    多尺度模板匹配。
    返回的 top_left / bottom_right 默认是屏幕绝对坐标。
    """
    best_score = -1.0
    best_top_left = None
    best_bottom_right = None
    best_scale = None

    for scale in scales:
        resized = cv2.resize(
            template,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LINEAR
        )
        th, tw = resized.shape[:2]
        sh, sw = screen.shape[:2]

        if tw > sw or th > sh:
            continue

        result = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = float(max_val)
            best_top_left = (max_loc[0] + origin[0], max_loc[1] + origin[1])
            best_bottom_right = (best_top_left[0] + tw, best_top_left[1] + th)
            best_scale = scale

    found = best_score >= threshold
    return found, best_score, best_top_left, best_bottom_right, best_scale


def match_score(screen: np.ndarray, template: np.ndarray) -> float:
    """
    返回模板在 screen 中的最佳匹配分数
    只返回分数，不负责业务判断
    """
    sh, sw = screen.shape[:2]
    th, tw = template.shape[:2]

    if tw > sw or th > sh:
        return -1.0

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


def match_score_multi_scale(
    screen: np.ndarray,
    template: np.ndarray,
    scales: list[float]
) -> tuple[float, Optional[float]]:
    """
    返回多尺度下最佳匹配分数和对应缩放倍数
    只返回结果，不负责业务判断
    """
    best_score = -1.0
    best_scale = None

    for scale in scales:
        resized = cv2.resize(
            template,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LINEAR
        )

        th, tw = resized.shape[:2]
        sh, sw = screen.shape[:2]

        if tw > sw or th > sh:
            continue

        result = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = float(max_val)
            best_scale = scale

    return float(best_score), best_scale


def crop_roi(image: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """
    裁切区域: (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = roi
    return image[y1:y2, x1:x2]


def ocr_text(image: np.ndarray, lang: str = "chi_sim+eng") -> str:
    processed = _prepare_for_ocr(image)
    text = pytesseract.image_to_string(processed, lang=lang)
    return _normalize_ocr_text(text)


def _prepare_for_ocr(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return gray


def _normalize_ocr_text(text: str) -> str:
    return text.strip().replace("\n", " ")


def box_center(
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    offset: tuple[int, int] = (0, 0),
) -> tuple[int, int]:
    """
    根据左上角和右下角坐标，返回中心点坐标，并支持偏移
    这里如果 top_left / bottom_right 是绝对坐标，则返回的也是绝对坐标。
    """
    center_x = (top_left[0] + bottom_right[0]) // 2 + offset[0]
    center_y = (top_left[1] + bottom_right[1]) // 2 + offset[1]
    return center_x, center_y


def point_offset(
    point: tuple[int, int],
    offset: tuple[int, int] = (0, 0),
) -> tuple[int, int]:
    """
    对一个点坐标应用偏移
    """
    return point[0] + offset[0], point[1] + offset[1]


def edge_image(
    image: np.ndarray,
    blur_ksize: int = 3,
    canny_low: int = 80,
    canny_high: int = 160,
) -> np.ndarray:
    """
    将图像转换为边缘图。
    适合背景杂乱、颜色变化频繁，但目标轮廓较稳定的场景。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if blur_ksize > 0:
        # 高斯核必须是奇数
        if blur_ksize % 2 == 0:
            blur_ksize += 1
        gray = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)

    edges = cv2.Canny(gray, canny_low, canny_high)
    return edges


def find_template_edge(
    screen: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
    origin: tuple[int, int] = (0, 0),
    blur_ksize: int = 3,
    canny_low: int = 80,
    canny_high: int = 160,
) -> tuple[bool, float, Optional[tuple[int, int]], Optional[tuple[int, int]]]:
    """
    在边缘图上做模板匹配。
    返回的坐标仍然是屏幕绝对坐标（受 origin 影响）。
    """
    screen_edge = edge_image(
        screen,
        blur_ksize=blur_ksize,
        canny_low=canny_low,
        canny_high=canny_high,
    )
    template_edge = edge_image(
        template,
        blur_ksize=blur_ksize,
        canny_low=canny_low,
        canny_high=canny_high,
    )

    result = cv2.matchTemplate(screen_edge, template_edge, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        h, w = template_edge.shape[:2]
        top_left = (max_loc[0] + origin[0], max_loc[1] + origin[1])
        bottom_right = (top_left[0] + w, top_left[1] + h)
        return True, float(max_val), top_left, bottom_right

    return False, float(max_val), None, None


def find_template_multi_scale_edge(
    screen: np.ndarray,
    template: np.ndarray,
    scales: list[float],
    threshold: float = 0.8,
    origin: tuple[int, int] = (0, 0),
    blur_ksize: int = 3,
    canny_low: int = 80,
    canny_high: int = 160,
) -> tuple[bool, float, Optional[tuple[int, int]], Optional[tuple[int, int]], Optional[float]]:
    """
    在边缘图上做多尺度模板匹配。
    返回的坐标仍然是屏幕绝对坐标。
    """
    screen_edge = edge_image(
        screen,
        blur_ksize=blur_ksize,
        canny_low=canny_low,
        canny_high=canny_high,
    )

    best_score = -1.0
    best_top_left = None
    best_bottom_right = None
    best_scale = None

    sh, sw = screen_edge.shape[:2]

    for scale in scales:
        resized = cv2.resize(
            template,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LINEAR
        )
        template_edge = edge_image(
            resized,
            blur_ksize=blur_ksize,
            canny_low=canny_low,
            canny_high=canny_high,
        )

        th, tw = template_edge.shape[:2]
        if tw > sw or th > sh:
            continue

        result = cv2.matchTemplate(screen_edge, template_edge, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = float(max_val)
            best_top_left = (max_loc[0] + origin[0], max_loc[1] + origin[1])
            best_bottom_right = (best_top_left[0] + tw, best_top_left[1] + th)
            best_scale = scale

    found = best_score >= threshold
    return found, best_score, best_top_left, best_bottom_right, best_scale


def match_score_edge(
    screen: np.ndarray,
    template: np.ndarray,
    blur_ksize: int = 3,
    canny_low: int = 80,
    canny_high: int = 160,
) -> float:
    """
    只返回边缘图模板匹配分数，不返回位置。
    适合在 main 中自己比较多个模板谁更像。
    """
    screen_edge = edge_image(
        screen,
        blur_ksize=blur_ksize,
        canny_low=canny_low,
        canny_high=canny_high,
    )
    template_edge = edge_image(
        template,
        blur_ksize=blur_ksize,
        canny_low=canny_low,
        canny_high=canny_high,
    )

    sh, sw = screen_edge.shape[:2]
    th, tw = template_edge.shape[:2]

    if tw > sw or th > sh:
        return -1.0

    result = cv2.matchTemplate(screen_edge, template_edge, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)