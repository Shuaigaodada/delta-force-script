import logging
import colorlog


def build_logger():
    logger = colorlog.getLogger("main")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = colorlog.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)s%(reset)s | %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )

    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger: logging.Logger | None = None
"""全局日志记录器，使用 colorlog 输出彩色日志"""
if logger is None:
    logger = build_logger()