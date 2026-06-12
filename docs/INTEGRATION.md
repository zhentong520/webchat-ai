# WebChat AI — 多应用接入指南

正式代码目录：**`E:/webchat-ai`**（长期维护用这个，原 `E:/SKILLS/wx4py-mcp` 可保留作备份）

---

## 先搞清楚三件事

| 层次 | 是什么 | 只装 Skill 够吗？ |
|------|--------|-------------------|
| **1. 代码 + 依赖** | `E:/webchat-ai` + `pip install -e .` + 微信 PC 登录 | ❌ 必须 |
| **2. MCP 服务** | 让 Agent **调用工具**（发消息、读历史、通话） | 对话里用 MCP 时必须 |
| **3. Skill** | 告诉 Agent **怎么用**（命令、路径、规则） | 辅助，不能代替 1 和 2 |

**结论：只复制 Skill 不够。** 至少还要安装 Python 包；要在对话里发微信，还要配 MCP。

**监听脚本**（私聊/群自动回复）不依赖 MCP，任意终端运行 PowerShell 即可。

---

## 共用配置（所有应用推荐）

```powershell
cd E:/webchat-ai
pip install -e .

# 填写模型 API（一次，其他 Python 项目也能读）
python E:/webchat-ai/scripts/ai-config.py --init
notepad E:/webchat-ai/config/ai-config.json
```

其他 Python 应用读模型：

```python
import sys
sys.path.insert(0, r"E:/webchat-ai")
from wx4py_mcp.ai_config import load_ai_config
cfg = load_ai_config()  # 或 profile="glm"
```

---

## WorkBuddy

### A. 对话里发微信（MCP 工具）

编辑 **`C:/Users/Administrator/.workbuddy/.mcp.json`**：

```json
{
  "mcpServers": {
    "webchat-ai": {
      "type": "stdio",
      "command": "C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe",
      "args": ["-m", "wx4py_mcp"],
      "cwd": "E:/webchat-ai",
      "description": "WebChat AI - 微信发消息/监听/通话"
    }
  }
}
```

> AI 模型优先读 `E:/webchat-ai/config/ai-config.json`，一般**不必**在 mcp.json 里再写 API Key。

重启 WorkBuddy 后，Agent 可用：`wechat_send`、`wechat_status`、`wechat_video_call` 等。

### B. Skill（让 Agent 知道命令）

把 Skill 放到 WorkBuddy 技能目录（二选一）：

```powershell
# 方式1：复制
Copy-Item E:/webchat-ai/SKILL.md C:/Users/Administrator/.workbuddy/skills/webchat-ai/SKILL.md -Force

# 方式2：E 盘主仓库（若已联接）
Copy-Item E:/webchat-ai/SKILL.md E:/SKILLS/webchat-ai/SKILL.md -Force
```

### C. 后台自动回复（不经过对话）

```powershell
powershell -File E:/webchat-ai/scripts/listen-wechat.ps1 Air
powershell -File E:/webchat-ai/scripts/listen-wechat-group.ps1 测试群1
```

---

## Cursor

### MCP

合并到 Cursor MCP 配置（或 `.cursor/mcp.json`），内容与 WorkBuddy 相同，`cwd` 指向 `E:/webchat-ai`。

### Skill

```powershell
Copy-Item E:/webchat-ai/SKILL.md C:/Users/Administrator/.cursor/skills/webchat-ai/SKILL.md -Force
```

或通过 `E:/agent-hub/cursor/skills` 联接（若你环境已配置 junction）。

---

## OpenClaw

**已配置（2026-06-07）** — `~/.openclaw/openclaw.json`：

- MCP：`mcp.servers.webchat-ai` → `cwd: E:/webchat-ai`
- Skill：`~/.openclaw/skills/webchat-ai/SKILL.md`，`skills.entries.webchat-ai.enabled: true`
- 旧 `wx4py-mcp` skill 已禁用

修改 MCP 后需 **重启 OpenClaw Gateway**：

```powershell
openclaw gateway restart
```

OpenClaw 若已配 MiniMax（`openclaw.json` → models.providers），**微信 AI 回复仍优先用** `config/ai-config.json`；未填时自动回退 mmx / OpenClaw / WorkBuddy。

---

## 其他 Python / Node 应用

| 需求 | 做法 |
|------|------|
| 只读 AI 配置 | `from wx4py_mcp.ai_config import load_ai_config` |
| 发一条微信 | `send_message_smart()`，见 README |
| 长期监听 | 子进程跑 `poll_private_chat.py` / `poll_group_chat.py` |
| HTTP 服务 | 自行包一层 FastAPI 调 `wx4py_mcp`（本项目未内置） |

---

## 检查清单

- [ ] `E:/webchat-ai` 存在且 `pip install -e .` 成功
- [ ] `config/ai-config.json` 已填 `api_key`（或本机 mmx 可用）
- [ ] 微信 PC 已登录
- [ ] 要用 MCP → 对应应用的 mcp.json 已配且 **cwd=E:/webchat-ai**
- [ ] 要让 Agent 懂命令 → Skill 已复制到该应用 skills 目录
- [ ] 要自动回复 → 单独运行 `listen-wechat.ps1` / `listen-wechat-group.ps1`

---

## 原 wx4py-mcp 目录

`E:/SKILLS/wx4py-mcp/` 为开发过程目录，**新接入请统一用 `E:/webchat-ai`**。  
WorkBuddy 里若仍指向旧路径，请改为 `E:/webchat-ai`。
