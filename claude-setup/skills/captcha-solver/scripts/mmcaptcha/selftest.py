"""Offline checks for parser and coordinate invariants."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

if __package__:
    from . import engines, presets
else:
    # laohe: keep the documented direct-file selftest independent of cwd.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import engines
    import presets


class _FakeResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"output_text": "ok"})()


class _FakeClient:
    def __init__(self):
        self.responses = _FakeResponses()


def main() -> int:
    assert presets.parse_grid("analysis 9\n1,3,3", 6) == [1, 3]
    assert presets.grid_center(1, 2, 3, 300, 200) == (50, 50)
    assert presets.parse_chars('{"1":["带","伴"],"2":[]}') == {1: ["带", "伴"], 2: []}
    assert presets.parse_gap_x("187") == 187
    assert presets.parse_norm_coords("100,200;1200,1;300，400") == [(100, 200), (300, 400)]
    assert presets.to_pixels([(500, 250)], 300, 200) == [(150, 50)]
    client = _FakeClient()
    engine = object.__new__(engines.DoubaoEngine)
    engine.model = "test-model"
    engine._client = client
    assert engine.ask(b"image", "prompt", timeout=7) == "ok"
    assert client.responses.kwargs["timeout"] == 7
    print("mmcaptcha selftest: 7/7 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
