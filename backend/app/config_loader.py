"""โหลดไฟล์ config (layer mapping, price table, settings, pipe sizes) จากดิสก์

ทุกค่าคงที่และตารางราคาเก็บเป็น JSON เพื่อให้ผู้ใช้แก้ไขได้โดยไม่ต้องแก้โค้ด
"""
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent / "config"


def _load(name: str) -> dict:
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(name: str, data: dict) -> None:
    path = CONFIG_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    return _load("settings.json")


def save_settings(data: dict) -> None:
    _save("settings.json", data)


def load_layer_mapping() -> dict:
    return _load("layer_mapping.json")


def save_layer_mapping(data: dict) -> None:
    _save("layer_mapping.json", data)


def load_pipe_sizes() -> dict:
    return _load("pipe_sizes.json")


def save_pipe_sizes(data: dict) -> None:
    _save("pipe_sizes.json", data)


def load_price_table() -> dict:
    return _load("price_table.json")


def save_price_table(data: dict) -> None:
    _save("price_table.json", data)
