"""Unified entrypoint for grid, click, order, and slider recognition."""

from __future__ import annotations

from . import presets
from .engines import get_engine

_lao_1_he = "munian_laohe"


class Result:
    __slots__ = ("tiles", "coords", "gap_x", "chars", "text", "raw", "engine")

    def __init__(self, engine: str = ""):
        self.tiles = []
        self.coords = []
        self.gap_x = None
        self.chars = {}
        self.text = ""
        self.raw = ""
        self.engine = engine

    def __repr__(self):
        return (
            f"<Result engine={self.engine} tiles={self.tiles} coords={self.coords} "
            f"gap_x={self.gap_x} chars={self.chars}>"
        )


class MultimodalRecognizer:
    def __init__(self, engine: str = "doubao", api_key: str | None = None, model: str | None = None):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if model:
            kwargs["model"] = model
        self.engine_name = engine
        self.engine = get_engine(engine, **kwargs)

    def _ask(self, image_bytes_list, prompt, mime="image/png"):
        return self.engine.ask(image_bytes_list, prompt, mime=mime)

    def grid_select(self, image_bytes, instruction, rows=2, cols=3) -> Result:
        raw = self._ask(image_bytes, presets.grid_select_prompt(instruction, rows, cols, mode="image"))
        result = Result(self.engine_name)
        result.raw = raw
        result.tiles = presets.parse_grid(raw, rows * cols)
        return result

    def text_grid_select(self, image_bytes, instruction, rows=2, cols=3) -> Result:
        raw = self._ask(image_bytes, presets.grid_select_prompt(instruction, rows, cols, mode="text"))
        result = Result(self.engine_name)
        result.raw = raw
        result.tiles = presets.parse_grid(raw, rows * cols)
        return result

    def read_chars(self, image_bytes, rows=2, cols=3) -> Result:
        raw = self._ask(image_bytes, presets.read_chars_prompt(rows, cols))
        result = Result(self.engine_name)
        result.raw = raw
        result.chars = presets.parse_chars(raw)
        return result

    def slider_gap(self, bg_bytes, gap_bytes) -> Result:
        """Compare a complete background with a same-size background containing the gap."""
        raw = self._ask([bg_bytes, gap_bytes], presets.slider_gap_prompt())
        result = Result(self.engine_name)
        result.raw = raw
        result.gap_x = presets.parse_gap_x(raw)
        return result

    def free_click(self, image_bytes, instruction, n=None) -> Result:
        raw = self._ask(image_bytes, presets.free_click_prompt(instruction, n))
        result = Result(self.engine_name)
        result.raw = raw
        result.coords = presets.parse_norm_coords(raw)
        return result

    def order_click(self, image_bytes, instruction) -> Result:
        raw = self._ask(image_bytes, presets.order_click_prompt(instruction))
        result = Result(self.engine_name)
        result.raw = raw
        result.coords = presets.parse_norm_coords(raw)
        return result

    @staticmethod
    def to_pixels(norm_coords, width, height):
        return presets.to_pixels(norm_coords, width, height)

    @staticmethod
    def grid_center(tile, rows, cols, width, height):
        return presets.grid_center(tile, rows, cols, width, height)
