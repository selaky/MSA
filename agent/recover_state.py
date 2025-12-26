from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Final, Optional


POTION_KEYS: Final[tuple[str, ...]] = (
    "ap_big",
    "ap_small",
    "bc_big",
    "bc_small",
)


@dataclass
class RecoverState:
    used_count: dict[str, int] = field(
        default_factory=lambda: {key: 0 for key in POTION_KEYS}
    )


_STATE_BY_TASK_ID: dict[int, RecoverState] = {}


def reset_state(task_id: int) -> None:
    """重置指定任务的状态，并清理所有其他旧任务的状态以防止内存泄漏。"""
    # 清理所有旧的 task_id，只保留当前的
    _STATE_BY_TASK_ID.clear()
    _STATE_BY_TASK_ID[task_id] = RecoverState()


def get_state(task_id: int) -> RecoverState:
    state = _STATE_BY_TASK_ID.get(task_id)
    if state is None:
        raise RuntimeError(
            f"恢复状态未初始化：task_id={task_id}。"
            "请确认跑图主流程中的【初始化吃药数据】节点已执行，且其动作已绑定到自定义初始化 Action。"
        )
    return state


def parse_custom_param_json(param_str: str, *, where: str) -> Any:
    """解析 MaaFramework 传入的 custom_*_param 字符串（通常是 JSON）。"""

    raw = (param_str or "").strip()
    if raw == "" or raw == "null":
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"{where} 的参数不是合法 JSON：{raw!r}") from e


_INT_RE: Final[re.Pattern[str]] = re.compile(r"^-?\d+$")


def coerce_int(value: Any, *, where: str) -> int:
    """将参数值强制转换为 int；失败时抛出明确异常，避免静默吞错。"""

    if isinstance(value, bool):
        raise TypeError(f"{where} 期望 int，但拿到 bool：{value!r}")

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        s = value.strip()
        if not _INT_RE.fullmatch(s):
            raise ValueError(f"{where} 期望整数格式字符串，但拿到：{value!r}")
        return int(s)

    raise TypeError(f"{where} 期望 int/str，但拿到：{type(value).__name__} {value!r}")


_DIGITS_RE: Final[re.Pattern[str]] = re.compile(r"^\d+$")


def parse_ocr_digits(text: str, *, node_name: str, max_value: int = 99999) -> int:
    """解析 OCR 结果为纯数字（仅支持 0-9），不做乘号等兼容。

    Args:
        text: OCR 识别的文本
        node_name: 节点名称，用于错误信息
        max_value: 允许的最大值，默认 99999

    Returns:
        解析后的整数值

    Raises:
        ValueError: 当 OCR 结果不是纯数字或超出合理范围时
    """
    s = (text or "").strip()
    if not _DIGITS_RE.fullmatch(s):
        raise ValueError(f"OCR 结果不是纯数字：node={node_name} text={text!r}")

    value = int(s)
    if value < 0 or value > max_value:
        raise ValueError(
            f"OCR 结果超出合理范围：node={node_name} text={text!r} "
            f"value={value} (期望范围: 0-{max_value})"
        )

    return value


def find_last_node_detail(task_detail: Any, *, node_name: str) -> Any:
    """从 task_detail.nodes 中反向查找最后一次出现的节点执行详情。"""

    for node_detail in reversed(getattr(task_detail, "nodes", []) or []):
        if getattr(node_detail, "name", None) == node_name:
            return node_detail

    raise RuntimeError(
        f"在 TaskDetail 中找不到节点执行记录：{node_name}。"
        "请确认 pipeline 流程确实执行到了统计节点，并且节点名未被改动。"
    )


def read_ocr_int_from_node(task_detail: Any, *, node_name: str) -> int:
    node_detail = find_last_node_detail(task_detail, node_name=node_name)
    reco_detail = getattr(node_detail, "recognition", None)
    if reco_detail is None:
        raise RuntimeError(f"节点缺少 recognition 详情：{node_name}")

    best = getattr(reco_detail, "best_result", None)
    if best is None:
        raise RuntimeError(f"OCR 未产生 best_result：{node_name}")

    text: Optional[str] = getattr(best, "text", None)
    if text is None:
        raise RuntimeError(
            f"节点 best_result 不包含 text 字段，无法作为 OCR 结果读取：{node_name}"
        )

    return parse_ocr_digits(text, node_name=node_name)
