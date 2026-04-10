from __future__ import annotations
import sys
from pathlib import Path

def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

ROOT_DIR = app_root()
DATA_DIR = ROOT_DIR / "data"
CUSTOM_DIR = ROOT_DIR / "custom"
LIBS_DIR = ROOT_DIR / "libs"

def data_path(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)

def custom_path(*parts: str) -> Path:
    return CUSTOM_DIR.joinpath(*parts)

def libs_path(*parts: str) -> Path:
    return LIBS_DIR.joinpath(*parts)