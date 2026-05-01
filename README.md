# Gcode MCP Server

**麒麟OS 智能运维Agent — 执行层**

MCP Server 负责接收 LLM 推理结果，执行实际的系统操作。通过三层安全机制确保每次操作都可控、可审计。

## 架构

```
用户自然语言
    ↓
gcode-security-guard (m1)  ← 意图过滤 + 审计
    ↓ Unix Domain Socket
gcode-mcp-server (本仓库)  ← MCP 协议 + 命令执行
    ↓
麒麟OS (systemd / rpm / journalctl / ...)
```

## 安全护栏

| 层级 | 机制 | 说明 |
|------|------|------|
| 入口 | 高危命令正则拦截 | rm -rf、mkfs、dd、chmod 777 等直接 BLOCKED |
| 参数 | 注入字符校验 | 拒绝路径穿越、命令拼接 |
| 确认 | dry-run + human-in-the-loop | 高风险操作先预览，人工确认后执行 |
| 执行 | seccomp 白名单 + resource limit | 仅开放 36 个安全系统调用，512MB 内存上限 |
| 审计 | audit_id 全链路追踪 | 每个 Tool 调用生成唯一 ID，推送至审计层 |

## 项目结构

```
src/
├── contracts/         # 接口契约（与 m1 约定）
│   └── types.py       # SessionContext, ToolCallRecord, ToolResult, RiskLevel
├── mcp_server/        # MCP Server 入口
│   └── __init__.py    # FastMCP, session 管理, Tool 注册
├── tools/             # MCP Tool（3类12个）
│   ├── readonly.py    # sys_info, ps_list, df_h, netstat, journalctl
│   ├── metrics.py     # cpu_usage, mem_usage, io_stat, disk_health
│   └── management.py  # service_restart, pkg_install, service_status
└── executor/          # 执行层
    ├── executor.py    # 命令执行 + 权限门禁
    └── sandbox.py     # seccomp 配置 + 资源限制
```

## 安装

```bash
git clone https://github.com/yGGGgGGGy/gcode-mcp-server.git
cd gcode-mcp-server
pip install -e .
```

## 启动

**开发模式（stdio）：**

```bash
python -m src.mcp_server
```

**生产模式（Unix Socket，与 m1 对接）：**

```bash
# 创建 socket 目录
sudo mkdir -p /run/gcode
sudo chown gcode:gcode /run/gcode

# 启动（需与 security-guard 配合）
python -m src.mcp_server --socket /run/gcode/gcode-dp1.sock
```

**systemd 服务：**

```ini
# /etc/systemd/system/gcode-mcp-server.service
[Unit]
Description=Gcode MCP Server — 智能运维执行层
After=network.target gcode-security-guard.service

[Service]
Type=simple
User=gcode
Group=gcode
ExecStart=/usr/bin/python3 -m src.mcp_server --socket /run/gcode/gcode-dp1.sock
Restart=on-failure
RestartSec=5
SystemCallFilter=@system-service
MemoryMax=512M

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gcode-mcp-server
```

## MCP Tool 列表

### 只读感知（risk: low）

| Tool | 功能 | 示例 |
|------|------|------|
| `sys_info` | 系统信息（内核、架构、麒麟版本） | 无参数 |
| `ps_list` | 进程列表 | 无参数 |
| `df_h` | 磁盘使用 | 无参数 |
| `netstat` | 网络连接 | 无参数 |
| `journalctl` | 系统日志 | `service="nginx", lines=100` |

### 指标采集（risk: low）

| Tool | 功能 | 示例 |
|------|------|------|
| `cpu_usage` | CPU 使用率 | 无参数 |
| `mem_usage` | 内存 + Swap | 无参数 |
| `io_stat` | 磁盘 IO | 无参数 |
| `disk_health` | 磁盘健康 | `path="/data"` |

### 管理执行（risk: medium/high）

| Tool | 功能 | 确认 |
|------|------|------|
| `service_status` | 服务状态 | 否 |
| `service_restart` | 重启服务 | **需确认** |
| `pkg_install` | 安装 RPM 包 | **需确认** |

## API 协议

### 输入（来自 security-guard）

```json
{
  "session_id": "uuid",
  "original_input": "重启 nginx 服务",
  "filtered_input": "重启 nginx 服务",
  "risk_score": 0.15,
  "risk_verdict": "safe",
  "capability_set": ["readonly", "metrics", "management"],
  "reason": "运维操作，无高危特征"
}
```

### 输出（推送给审计层）

```json
{
  "audit_id": "uuid",
  "session_id": "uuid",
  "step_id": "step-3",
  "parent_step_id": "step-2",
  "tool_name": "service_restart",
  "params": {"service_name": "nginx"},
  "result": {"stdout": "", "stderr": "", "rc": 0},
  "risk_level": "high",
  "timestamp": 1714567890.123,
  "executor_user": "agent-exec"
}
```

### 高危拦截示例

```
用户: "帮我执行 rm -rf /etc/nginx"
响应:
{
  "success": false,
  "error": "BLOCKED: 匹配高危模式 'rm.*-rf'",
  "audit_id": "uuid",
  "needs_confirmation": false
}
```

### 需确认示例

```
用户: "安装 nginx"
响应:
{
  "success": true,
  "data": {
    "dry_run": "nginx.x86_64  1.24.0  @base",
    "needs_confirmation": true
  },
  "audit_id": "uuid",
  "needs_confirmation": true
}
```

## 麒麟OS 适配

| 项目 | 说明 |
|------|------|
| 包管理 | dnf/rpm，兼容 yum |
| 服务管理 | systemd（`systemctl`） |
| 日志 | journalctl，对接 auditd |
| 安全 | SELinux 策略 + seccomp 白名单 |
| 容器 | podman 可选隔离 |

## 关联项目

- [Gcode](https://github.com/yGGGgGGGy/Gcode) — 主项目
- [gcode-security-guard](https://github.com/yGGGgGGGy/gcode-security-guard) — 安全护栏（意图过滤 + 审计，m1 负责）
