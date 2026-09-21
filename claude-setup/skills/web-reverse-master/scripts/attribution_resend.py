#!/usr/bin/env python3
"""归因步骤1的离线分类器：同一请求同字节最多总计 3 次 → 判定「恒定 / 有状态 / 样本不足」。

对应 web-reverse-master SKILL.md「证据与停止条件」的同字节重发限制：
  - 恒定（同输入恒定响应）≠ 算法错。时间戳缺失/缺前置接口同样会恒拒 → 必须做原版对照(步骤2)。
  - 漂移 / 随量降级 → 服务端有状态计分 → 跳到维度轮换(步骤4)。

本模块只做**离线判定**：调用方负责真正重发（requests / curl_cffi）并把每次的
status + 一个稳定信号（响应体哈希或长度）喂进来。不联网，可被 selftest 覆盖。

注意：本文件在仓库根 scripts/ 与 .claude/skills/web-reverse-master/scripts/
各存一份，必须保持字节一致（两处 selftest 的 attribution case 都会校验）。
"""

from __future__ import annotations

from typing import Sequence, Mapping, Any


_LAOHE_MAX_TOTAL_REQUESTS = 3
MIN_SAMPLES = _LAOHE_MAX_TOTAL_REQUESTS
MAX_SAMPLES = _LAOHE_MAX_TOTAL_REQUESTS


def classify_resend(samples: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    """判定同字节重发结果。

    Args:
        samples: 每项含 ``status``（HTTP 状态码）与 ``signal``（响应体哈希/长度等稳定信号）。
                 应为「逐字节相同的请求」不超过 3 次（含首次发送）的记录。

    Returns:
        (verdict, reason)：
          - ``"constant"``  3 次同输入恒定响应 → 仅说明当前请求未见随量漂移，去做原版对照。
          - ``"stateful"``  从第 2 个样本起一旦响应漂移/降级 → 立即停止重发。
          - ``"insufficient"`` 1–2 个恒定样本不足以证明恒定。
          - ``"invalid"`` 超过硬上限或样本缺少必需字段，拒绝归因。
    """
    n = len(samples)
    if n > MAX_SAMPLES:
        return ("invalid", f"同字节请求硬上限为总计 {MAX_SAMPLES} 次，收到 {n} 个样本；停止线上重发")
    for index, sample in enumerate(samples):
        if not isinstance(sample, Mapping) or "status" not in sample or "signal" not in sample:
            return ("invalid", f"样本 {index} 缺少 status/signal，拒绝归因")

    statuses = {s["status"] for s in samples}
    signals = {s["signal"] for s in samples}

    if n >= 2 and (len(statuses) > 1 or len(signals) > 1):
        return (
            "stateful",
            "响应已随重发漂移/降级：立即停止同字节重发，转维度轮换与对照实验",
        )

    if n < MIN_SAMPLES:
        return ("insufficient", f"当前 {n} 次响应恒定；须到总计 3 次才能结束恒定性实验")

    return (
        "constant",
        "3 次同字节恒定响应：只说明当前请求未见随量漂移；算法错误或无记忆校验均未证实→ "
        "做原版对照(§4.1 步骤2)，未两证前禁说「被风控 / 算不出」",
    )


if __name__ == "__main__":  # 手动 smoke
    demo_constant = [{"status": 403, "signal": "h0"} for _ in range(3)]
    demo_drift = [{"status": 403, "signal": f"h{i}"} for i in range(3)]
    print(classify_resend(demo_constant))
    print(classify_resend(demo_drift))
    print(classify_resend(demo_constant[:2]))
