"""Gcode 接口契约 — dp1 与 m1 模块间数据格式约定"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskVerdict(str, Enum):
    SAFE = "safe"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


@dataclass
class SessionContext:
    """意图过滤层产出 → 传给 MCP Server"""
    session_id: str
    original_input: str
    filtered_input: str
    risk_score: float               # 0.0~1.0，0=安全
    risk_verdict: RiskVerdict
    capability_set: set[str]        # 允许的 tool 类别 {"readonly","metrics","management"}
    reason: str                     # 过滤决策理由


@dataclass
class ToolCallRecord:
    """MCP 执行层产出 → 推给审计层"""
    audit_id: str
    session_id: str
    step_id: str
    parent_step_id: str | None
    tool_name: str
    params: dict[str, Any]
    result: dict[str, Any] | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    timestamp: float = 0.0
    executor_user: str = "agent-exec"


@dataclass
class ToolResult:
    """统一 Tool 返回信封"""
    success: bool
    data: Any
    audit_id: str
    error: str | None = None
    needs_confirmation: bool = False
