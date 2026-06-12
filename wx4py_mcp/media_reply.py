"""Format parsed image/document content for direct WeChat reply (no AI chat)."""

from __future__ import annotations

import re

_MD_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_NUMBERED_SECTION = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\d+[).、]\s*|[-*]\s*)?(?:提取|可见|文字|内容|概要|描述|图片)[：:]\s*",
    re.MULTILINE | re.IGNORECASE,
)
_PREFIX_TAGS = re.compile(r"^\[(?:图片|文件|文档)\]\s*")


def normalize_parsed_text(raw: str) -> str:
    """Clean model output into plain text suitable for WeChat."""
    text = (raw or "").strip()
    if not text:
        return "未能识别出有效内容，请换一张更清晰的图片或重新发送文件。"
    text = _PREFIX_TAGS.sub("", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_BOLD.sub(r"\1", text)
    text = text.replace("**", "")
    lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        line = _NUMBERED_SECTION.sub("", line).strip()
        if line:
            lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned or "未能识别出有效内容，请换一张更清晰的图片或重新发送文件。"


def build_direct_media_reply(msg_type: str, parsed_content: str) -> str:
    """Return organized content to send back directly."""
    body = normalize_parsed_text(parsed_content)
    if msg_type == "image":
        if body.startswith("【") or body.startswith("——"):
            return body
        return f"【图片内容整理】\n{body}"
    if msg_type == "document":
        if body.startswith("【"):
            return body
        return f"【文档内容整理】\n{body}"
    return body
