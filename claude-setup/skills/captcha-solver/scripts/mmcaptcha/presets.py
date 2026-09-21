"""Prompt presets, deterministic parsers, and coordinate conversion."""

from __future__ import annotations

import json
import re

_lao_1_he = "munian_laohe"
NORM = 1000


def _grid_desc(rows: int, cols: int) -> str:
    return f"{cols}列{rows}行共{rows * cols}格, 编号按行从左到右、从上到下: " + " / ".join(
        f"第{row + 1}行=" + ",".join(str(row * cols + col + 1) for col in range(cols))
        for row in range(rows)
    )


def grid_select_prompt(instruction: str, rows: int = 2, cols: int = 3, mode: str = "image") -> str:
    desc = _grid_desc(rows, cols)
    if mode == "text":
        return (
            f"这是验证码图片, {desc}。每格里嵌有3D立体或艺术化渲染的扭曲汉字(一格可能多字)。\n"
            f"题目:{instruction}\n"
            "选格规则: '和/且'是同一格内的交集；'或'是并集；'包含X不含Y'是差集。"
            "逐格辨认后，最后一行只输出格子编号，逗号分隔；没有则输出 none。"
        )
    return (
        f"这是验证码图片, {desc}。\n"
        f"题目:请选出画面内容符合描述「{instruction}」的图片。\n"
        "逐格识别真实内容，注意区分物体与玩具或仿制品。"
        "最后一行只输出格子编号，逗号分隔；没有则输出 none。"
    )


def parse_grid(text: str, total: int) -> list[int]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    source = lines[-1] if lines else ""
    if source.lower() == "none":
        return []
    if not re.fullmatch(r"[0-9]+(?:\s*[,，]\s*[0-9]+)*", source):
        return []
    return sorted({int(value) for value in re.split(r"[,，]", source) if 1 <= int(value) <= total})


def grid_center(tile: int, rows: int, cols: int, width: int, height: int) -> tuple[int, int]:
    if any(type(value) is not int or value <= 0 for value in (rows, cols, width, height)):
        raise ValueError("grid and image dimensions must be positive integers")
    if type(tile) is not int:
        raise ValueError("tile must be an integer")
    if tile < 1 or tile > rows * cols:
        raise ValueError(f"tile must be in 1..{rows * cols}")
    row, col = divmod(tile - 1, cols)
    cell_width, cell_height = width / cols, height / rows
    return int(col * cell_width + cell_width / 2), int(row * cell_height + cell_height / 2)


def read_chars_prompt(rows: int = 2, cols: int = 3) -> str:
    return (
        f"这是验证码图片, {_grid_desc(rows, cols)}。每格可能有1至3个扭曲汉字或为空。"
        "逐格辨认，只输出 JSON 对象；键为格子编号，值为该格汉字数组。"
    )


def parse_chars(text: str) -> dict[int, list[str]]:
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.S)
    raw = match.group(0) if match else text
    out: dict[int, list[str]] = {}
    try:
        value = json.loads(raw)
        for key, chars in value.items():
            digits = str(key)
            if re.fullmatch(r"[0-9]+", digits) and int(digits) >= 1:
                items = chars if isinstance(chars, list) else [chars]
                if all(isinstance(item, str) for item in items):
                    out[int(digits)] = [item.strip() for item in items if item.strip()]
        return out
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        pass
    for line in text.splitlines():
        fallback = re.match(r"\s*[\"']?(\d+)[\"']?\s*[:：]\s*(.+)", line)
        if fallback and int(fallback.group(1)) >= 1:
            out[int(fallback.group(1))] = re.findall(r"[一-鿿]", fallback.group(2))
    return out


def slider_gap_prompt() -> str:
    return (
        "这是滑块验证码的两张图: 第一张是完整背景，第二张带缺口。"
        "对比并返回第二张图中缺口左上角的像素 X 坐标；只返回整数。"
    )


def parse_gap_x(text: str) -> int | None:
    value = text.strip()
    return int(value) if re.fullmatch(r"[0-9]+", value) else None


def free_click_prompt(instruction: str, n: int | None = None) -> str:
    count = f"(共{n}个目标)" if n else ""
    return (
        f"这是点选验证码图片。题目要求: {instruction}。找出目标{count}的中心点，"
        f"将 x/y 都归一化到 0~{NORM}。格式: x1,y1;x2,y2;...，只输出坐标。"
    )


def order_click_prompt(instruction: str) -> str:
    return (
        f"这是语序点选验证码图片。题目要求: {instruction}。"
        f"按正确点击顺序输出目标中心，x/y 归一化到 0~{NORM}。"
        "格式: x1,y1;x2,y2;...，只输出坐标。"
    )


def parse_norm_coords(text: str) -> list[tuple[int, int]]:
    out = []
    for item in re.split(r"[;；\n]", text):
        match = re.fullmatch(r"\s*([0-9]+)\s*[,，]\s*([0-9]+)\s*", item)
        if not match:
            continue
        x, y = int(match[1]), int(match[2])
        if 0 <= x <= NORM and 0 <= y <= NORM:
            out.append((x, y))
    return out


def to_pixels(norm_coords, width: int, height: int) -> list[tuple[int, int]]:
    """Convert the package's 0..1000 coordinates to in-image pixel indices."""
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers")
    out = []
    for x, y in norm_coords:
        if type(x) is not int or type(y) is not int or not (0 <= x <= NORM and 0 <= y <= NORM):
            raise ValueError("normalized coordinates must be integers in 0..1000")
        out.append((min(width - 1, x * width // NORM), min(height - 1, y * height // NORM)))
    return out
