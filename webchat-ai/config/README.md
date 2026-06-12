# 模型 API 配置说明

文件：`ai-config.json`（从 `ai-config.example.json` 复制）

JSON 不支持 `//` 注释，因此用 **`_comment` / `_description` / `_fields`** 字段写说明；程序读取时会自动忽略这些字段。

## 字段说明

| 字段 | 用途 |
|------|------|
| `_comment` | 文件整体说明 |
| `_fields` | 各配置项含义（字典） |
| `_description` | 当前块（默认或某个 profile）适合干什么 |
| `base_url` | API 根地址 |
| `model` | 模型名 |
| `api_key` | 密钥（必填才生效） |
| `active_profile` | 切换 `profiles` 里的预设，如 `"glm"` |

## 预设 profile 一览

| profile | 厂商 | 适合场景 |
|---------|------|----------|
| （顶层默认） | MiniMax | 微信中文对话，本项目实测 |
| `minimax` | MiniMax | 同默认，可单独填 Key |
| `glm` | 智谱 | 国内快、flash 便宜，适合高频自动回复 |
| `deepseek` | DeepSeek | 性价比高、对话均衡 |
| `qwen` | 通义千问 | 阿里云 DashScope 兼容接口 |

## 切换模型

```json
"active_profile": "glm"
```

并在对应 profile 的 `api_key` 填入密钥。

## 查看注释

```powershell
python E:/webchat-ai/scripts/ai-config.py --list
```
