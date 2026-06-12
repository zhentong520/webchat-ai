# WebChat AI — 微信智能自动化工具

> **版本：** 0.2.1  
> **路径：** `E:/webchat-ai`  
> **状态：** 已实测通过（2026-06-07）

基于 [wx4py](https://pypi.org/project/wx4py/) 的微信 PC 端自动化工具，无需 wxautox4 商业激活。支持 **私聊 / 群聊发消息**、**AI 自动回复监听**、**语音 / 视频通话**，可接入 WorkBuddy / Cursor MCP。

---

## 一、工具用途

| 场景 | 说明 |
|------|------|
| **自动回复** | 私聊或群聊有人发消息时，AI 自动回复（MiniMax 等） |
| **批量发消息** | 脚本或 MCP 给指定联系人 / 群发送文本 |
| **远程控制微信** | 通过 MCP 工具在 Cursor / WorkBuddy 中调用 |
| **通话触发** | 私聊收到「视频通话」「语音通话」指令时自动拨打 |
| **语音转文字** | 监听时自动识别对方语音消息，转写后交给 AI 回复 |
| **图片识别** | 监听时自动识别对方图片中的文字与内容，交给 AI 回复 |
| **群管理辅助** | 监听指定群，按规则回复（不含 @ 强制，与私聊相同逻辑） |

### 适用人群

- 需要用 AI 自动回微信私聊 / 群聊的开发者  
- 已在 PC 上登录微信，希望用 Python 自动操作的用户  
- 使用 WorkBuddy、Cursor MCP 的 Agent 工作流  

### 不适用

- 手机微信（仅 PC 版）  
- 未登录或频繁最小化到托盘且无法恢复的环境  
- 需要 100% 实时（本工具为轮询，默认 15 秒间隔）  

---

## 二、目录结构

```
E:/webchat-ai/
├── README.md                 ← 本文档（用途与使用说明）
├── start-all.bat             ← 一键开启监听（输入联系人）
├── stop-all.bat              ← 一键停止全部监听
├── docs/
│   ├── 操作手册.md             ← ★ 日常操作详细步骤（推荐阅读）
│   ├── INTEGRATION.md          ← WorkBuddy / OpenClaw 集成
│   └── 2026-06-07-功能整理.md  ← 开发细节与测试记录
├── wx4py_mcp/                ← 核心 Python 包
│   ├── open_chat.py          ← 打开会话（列表优先）
│   ├── last_message.py       ← 读最后一条 + 左/右气泡判断
│   ├── voice_message.py      ← 语音转文字
│   ├── image_message.py      ← 图片截图 + 视觉识别
│   ├── vision_client.py      ← MiniMax-M3 等多模态 API
│   ├── call_control.py       ← 语音/视频通话
│   ├── listen_control.py     ← 停止监听、通话指令
│   ├── state_store.py        ← 监听状态持久化
│   ├── conversation_memory.py ← 每用户对话记忆（上下文）
│   └── ...
├── scripts/                  ← 可执行脚本
│   ├── start_listen.py             ← 启动监听（支持 --interactive / --welcome）
│   ├── stop_listen.py              ← 停止监听
│   ├── listen-wechat.ps1           ← 单联系人私聊监听
│   ├── listen-wechat-group.ps1     ← 群聊监听
│   ├── stop-wechat.ps1             ← 停止私聊监听
│   ├── stop-wechat-group.ps1       ← 停止群聊监听
│   ├── poll_private_chat.py        ← 私聊轮询核心
│   ├── poll_group_chat.py          ← 群聊轮询核心
│   └── run_full_test.py            ← 全面自动化测试
├── config/
│   ├── listen-defaults.json        ← 默认监听对象（--all 时使用）
│   └── ai-config.json              ← AI 模型配置
├── mcp-config.example.json   ← MCP 配置示例
└── pyproject.toml
```

---

## 三、安装

### 环境要求

- Windows 10/11  
- 微信 PC 版已登录  
- Python 3.11（推荐）：`C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe`  
- AI：WorkBuddy / mmx 配置（`~/.mmx/config.json`）或环境变量 `WX4PY_AI_*`  

### 安装步骤

```powershell
cd E:/webchat-ai
pip install -e .
pip install wx4py mcp Pillow
```

---

## 四、使用方法

> **日常操作请看详细步骤：** [docs/操作手册.md](docs/操作手册.md)

### 4.0 一键开启 / 停止（最推荐）

| 操作 | 文件 | 说明 |
|------|------|------|
| **开启监听** | 双击 `E:\webchat-ai\start-all.bat` | 输入联系人 → 自动发自我介绍 → 后台监听 |
| **停止监听** | 双击 `E:\webchat-ai\stop-all.bat` | 停止全部私聊 + 群聊监听 |

**开启示例：**

1. 双击 `start-all.bat`
2. 输入 `coco`（或多个：`Air,coco`）
3. 回车，可选输入群名或跳过
4. 完成 — 任务栏会出现 `WebChat-私聊-coco` 最小化窗口

**停止方式：** 双击 `stop-all.bat`，或让对方发送 **`停止监听`**。

### 4.1 私聊 AI 监听（命令行）

监听指定联系人，对方发消息后 AI 自动回复。

```powershell
# 监听 Air（默认 15 秒轮询，WorkBuddy AI）
powershell -File E:/webchat-ai/scripts/listen-wechat.ps1 Air

# 监听多人
powershell -File E:/webchat-ai/scripts/start_workbuddy_private_reply.ps1 -Contacts "Air,娟子"

# Echo 测试（不调用 AI，回复「收到：xxx」）
powershell -File E:/webchat-ai/scripts/listen-wechat.ps1 Air -Echo
```

**停止：** 让对方发送 **`停止监听`** → 工具回复确认后**进程退出**。  
再次监听需重新运行上述命令（**启动时会自动检测最后一条对方消息**，含语音/图片识别，补回复后再进入轮询）。

**多媒体消息：** 对方发 **语音**、**图片** 或 **文件** 时：
- **图片/文档**：识别/解析后 **直接整理成文字发回**（不走闲聊 AI）
- **语音**：转文字后走 AI 回复

### 4.2 群聊 AI 监听

```powershell
# 监听测试群1
powershell -File E:/webchat-ai/scripts/listen-wechat-group.ps1 测试群1

# 多群
powershell -File E:/webchat-ai/scripts/start_workbuddy_group_reply.ps1 -Groups "测试群1,VIP群"
```

规则与私聊相同；**无**语音/视频通话。  
停止方式：群里发 **`停止监听`**。

### 4.3 手动发消息（Python）

```python
import sys
sys.path.insert(0, r"E:/webchat-ai")

from wx4py import WeChatClient
from wx4py_mcp.open_chat import send_message_smart

with WeChatClient() as wx:
    # 私聊
    send_message_smart(wx.chat_window, "Air", "你好", "contact")
    # 群聊
    send_message_smart(wx.chat_window, "测试群1", "大家好", "group")
```

### 4.4 MCP 接入（Cursor / WorkBuddy）

1. 复制 `mcp-config.example.json` 到客户端 MCP 配置  
2. 修改 `cwd` 为 `E:/webchat-ai`  
3. 启动：`python -m wx4py_mcp`  

| MCP 工具 | 功能 |
|----------|------|
| `wechat_send` | 发送文本 |
| `wechat_voice_call` | 发起语音通话 |
| `wechat_video_call` | 发起视频通话 |
| `wechat_get_history` | 读取聊天记录 |
| `wechat_send_file` | 发送文件 |
| `wechat_status` | 检查连接 |

### 4.5 私聊通话（指令触发）

监听运行中，对方发送：

| 指令 | 效果 |
|------|------|
| `视频通话` / `视频对话` | 自动点击标题栏 → 视频通话 |
| `语音通话` | 自动点击标题栏 → 语音通话 |

也可单独测试：

```powershell
python E:/webchat-ai/scripts/test_call.py Air --type video
```

---

## 五、模型 API 配置（供本工具及其他应用共用）

项目提供**统一配置文件**，填写一次即可被 WebChat AI 监听脚本及本机其他 Python 应用读取。

### 5.1 配置文件位置

```
E:/webchat-ai/config/
├── ai-config.example.json   ← 模板（可提交 git）
├── ai-config.json           ← 实际配置（含 api_key，勿提交）
└── README.md
```

### 5.2 首次配置

```powershell
# 1. 从模板生成 ai-config.json
python E:/webchat-ai/scripts/ai-config.py --init

# 2. 编辑 config/ai-config.json，填写 api_key
notepad E:/webchat-ai/config/ai-config.json

# 3. 查看是否生效
python E:/webchat-ai/scripts/ai-config.py --status
```

### 5.3 配置示例

```json
{
  "base_url": "https://api.minimaxi.com/v1",
  "model": "MiniMax-M2.5",
  "api_key": "你的API密钥",
  "api_format": "completions",
  "active_profile": "",
  "profiles": {
    "glm": {
      "base_url": "https://open.bigmodel.cn/api/paas/v4",
      "model": "glm-4-flash",
      "api_key": "智谱API密钥",
      "api_format": "completions"
    }
  }
}
```

- 顶层字段为**默认**配置  
- `profiles` 可预设多套（MiniMax / 智谱 / DeepSeek 等）  
- `active_profile` 填 `"glm"` 即切换到对应 profile  

### 5.4 读取优先级

1. 环境变量 `WX4PY_AI_*`（最高）  
2. **`config/ai-config.json`**（项目配置，推荐）  
3. 本机 mmx / OpenClaw / WorkBuddy models.json  

### 5.5 视觉模型（图片识别）

监听脚本读到对方 **图片消息** 时会：

1. 先截取聊天气泡 **缩略图**
2. 若分辨率过低或检测到 **模糊** → **双击** 打开预览并再次双击放大，截高清图
3. 调用 **MiniMax-M3** 提取文字并描述内容
4. **解析完成后自动关闭预览**，再交给 AI 回复

`config/ai-config.json` 可选 `vision` 段（见 `ai-config.example.json`）。**`api_key` 留空** 时自动复用本机 MiniMax Key。

也可通过环境变量覆盖：

```powershell
$env:WX4PY_VISION_API_KEY = "你的密钥"
$env:WX4PY_VISION_MODEL = "MiniMax-M3"
$env:WX4PY_VISION_BASE_URL = "https://api.minimaxi.com/v1"
```

### 5.6 其他应用如何调用

```python
import sys
sys.path.insert(0, r"E:/webchat-ai")

from wx4py_mcp.ai_config import load_ai_config, AI_CONFIG_FILE, config_status

# 读取配置
cfg = load_ai_config()
if cfg:
    print(cfg.base_url, cfg.model, cfg.source)

# 指定 profile
cfg_glm = load_ai_config(profile="glm")

# 自定义路径
cfg2 = load_ai_config(config_path=r"D:/my-app/ai-config.json")

# 状态检查（密钥脱敏）
print(config_status())
```

环境变量 `WEBCHAT_AI_CONFIG` 可指向任意 JSON 路径，便于多项目共用同一份配置。

---

## 六、工作原理

### 6.1 打开会话（不反复开关微信）

```
当前聊天已是目标？ → 是 → 直接操作
        ↓ 否
左侧会话列表有目标？ → 是 → 点击切换
        ↓ 否
Ctrl+F 搜索一次
```

### 6.2 监听回复

```
每 15 秒轮询
    ↓
打开目标会话，读最后一条消息
    ↓
左侧灰色（对方）？ → 否 → 跳过
    ↓ 是
已回复过 / 是自己发的？ → 是 → 跳过
    ↓ 否
AI 生成回复（带最近对话上下文）→ 发送 → 记录状态 + 写入对话记忆
```

### 6.3 防循环

- `__last_replied__`：同一条消息只回一次  
- `__outgoing__`：记录自己发出的内容，避免误当成对方消息  

### 6.4 对话记忆（上下文）

每个联系人 / 群 **单独一个本地 JSON 文件**，默认保留最近 **10 条**消息（用户 + AI 回复合计，约 5 轮对话），供 AI 回复时带入上下文。

| 路径 | 说明 |
|------|------|
| `~/.wx4py-mcp/memory/private/Air.json` | 私聊 Air 的对话记忆 |
| `~/.wx4py-mcp/memory/group/测试群1.json` | 群聊记忆 |

- 自动写入：每次成功回复后追加「用户消息 + AI 回复」  
- 自动读取：下次回复时把历史 messages 传给模型  
- 关闭记忆：`WX4PY_MEMORY_SIZE=0`  
- 调整条数：`WX4PY_MEMORY_SIZE=20`（默认 10）

---

## 七、状态与变量

### 状态文件（自动生成）

| 文件 | 说明 |
|------|------|
| `~/.wx4py-mcp/private_seen.json` | 私聊监听状态 |
| `~/.wx4py-mcp/group_seen.json` | 群聊监听状态 |
| `~/.wx4py-mcp/wechat.ui.lock` | UI 操作互斥锁 |

### 环境变量（可选）

| 变量 | 说明 |
|------|------|
| `WX4PY_AI_BASE_URL` | AI API 地址 |
| `WX4PY_AI_API_KEY` | API Key |
| `WX4PY_AI_MODEL` | 模型名 |
| `WX4PY_STATE_DIR` | 状态目录 |
| `WX4PY_MEMORY_SIZE` | 每用户对话记忆条数（默认 10，0=关闭） |

默认使用本机 WorkBuddy / mmx 的 MiniMax 配置，一般无需设置。

---

## 八、测试

```powershell
# 全面自动化测试（约 2 分钟）
python E:/webchat-ai/scripts/run_full_test.py

# 会话切换压力测试
python E:/webchat-ai/scripts/stress_test_session.py --case all
```

结果输出：`~/.wx4py-mcp/full-test-results.json`

---

## 九、注意事项

1. **名称必须完全一致**：联系人备注、群名大小写敏感（`Air` ≠ `air`）  
2. **微信保持可见**：最小化可能导致识别变慢，但不应反复开关窗口  
3. **不要同时跑两个监听进程**（私聊 + 群聊也建议分开测）  
4. **停止监听后需重新启动脚本**才能继续轮询  
5. 本工具基于 UI 自动化，微信大版本更新后可能需要适配  

---

## 十、常见问题

**Q：监听没反应？**  
A：检查是否已因「停止监听」退出；重新运行 `listen-wechat.ps1`。确认最后一条是对方发的（左侧灰色）。

**Q：一直走搜索、不开列表？**  
A：确保微信主窗口可见，目标在左侧列表中；见 `open_chat.py` 日志 `[session]`。

**Q：AI 回复失败？**  
A：检查 `~/.mmx/config.json` 或 `WX4PY_AI_*` 环境变量。

**Q：群聊和私聊区别？**  
A：群聊无通话功能，其余规则相同。

---

## 十一、更新记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.2.1 | 2026-06-09 | 一键启停 bat、输入联系人、启动自我介绍、图片/文档直回、对话记忆 |
| 0.2.1 | 2026-06-07 | 新增 config/ai-config.json 统一模型 API 配置 |
| 0.1.0 | 2026-06-07 | 私聊轮询、MCP 基础工具 |

---

## 十二、相关路径

- **E 盘记忆库：** `E:/agent-hub/memory/projects/wx4py-mcp.md`  
- **原开发目录：** `E:/SKILLS/wx4py-mcp/`（与本文档同步）  

如有问题，先看日志中的 `[session]`、`[Air]`、`[测试群1]` 前缀行。
