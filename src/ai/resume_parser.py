"""PDF 简历解析 — PDF → Markdown 转换"""

from __future__ import annotations

from pathlib import Path

import pymupdf4llm


def pdf_to_markdown(pdf_path: str) -> str:
    """将 PDF 简历转换为 Markdown 文本

    Args:
        pdf_path: PDF 文件路径

    Returns:
        Markdown 格式的简历文本

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 非 PDF 文件、内容为空（可能是扫描件）
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"简历文件不存在: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"仅支持 PDF 文件, 收到: {path.suffix}")

    md_text = pymupdf4llm.to_markdown(pdf_path)

    if not md_text or not md_text.strip():
        raise ValueError("PDF 解析结果为空。可能是扫描件(纯图片), 请提供含文字层的 PDF。")

    return md_text.strip()
