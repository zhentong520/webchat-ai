---
name: webchat-ai
description: 微信 PC 智能自动化（WebChat AI）。私聊/群聊发消息、AI 轮询监听、语音转文字、图片识别、语音视频通话。路径 E:/webchat-ai。触发词：webchat-ai、微信监听、微信 MCP。
version: 0.2.1
---

# WebChat AI

> 完整说明见 [`README.md`](README.md)

**路径：** `E:/webchat-ai`

```powershell
cd E:/webchat-ai && pip install -e .

# 私聊监听
powershell -File E:/webchat-ai/scripts/listen-wechat.ps1 Air

# 群聊监听
powershell -File E:/webchat-ai/scripts/listen-wechat-group.ps1 测试群1
```

详见 README.md。
