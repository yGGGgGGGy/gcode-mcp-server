# Gcode MCP Server

**麒麟OS 智能运维Agent — 执行层**

## 职责

- MCP 协议 Server 实现（FastMCP）
- 三层分级 Tool（只读感知 / 指标采集 / 管理执行）
- 命令执行器 + 安全沙箱（seccomp + 资源限制）
- 与 Security Guard 模块（m1）通过 SessionContext / ToolCallRecord 契约对接

## 架构

```
Security Guard(m1) → SessionContext → MCP Server(here) → 执行器 → OS
```

## 项目结构

```
src/
├── contracts/     # 接口契约（与 m1 约定）
│   └── types.py   # SessionContext, ToolCallRecord, ToolResult
├── mcp_server/    # MCP Server 入口
│   └── __init__.py
├── tools/         # MCP Tool 实现
│   ├── readonly.py    # 只读感知: sys_info, ps_list, df_h, netstat, journalctl
│   ├── metrics.py     # 指标采集: cpu_usage, mem_usage, io_stat, disk_health
│   └── management.py  # 管理执行: service_restart, pkg_install, service_status
└── executor/      # 执行层
    ├── executor.py    # 命令执行 + 权限门禁
    └── sandbox.py     # seccomp 配置 + 资源限制
```

## 安装

```bash
pip install -e .
```

## 运行

```bash
python -m src.mcp_server
```

## 安全机制

| 层级 | 机制 |
|------|------|
| 入口 | 高危命令正则拦截（rm -rf, mkfs, dd, chmod 777） |
| 参数 | 路径穿越/注入字符校验 |
| 执行 | seccomp 系统调用白名单 + resource limit |
| 审计 | 每个 ToolCall 生成 audit_id，对接审计层 |

## 麒麟OS 适配

- rpm/dnf 包管理
- systemd 服务管理
- SELinux 安全策略兼容
- auditd 审计日志打通

## 关联项目

- [Gcode](https://github.com/yGGGgGGGy/Gcode) — 主项目
- [gcode-security-guard](https://github.com/yGGGgGGGy/gcode-security-guard) — 安全护栏（意图过滤 + 审计）
