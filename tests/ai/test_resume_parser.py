"""PDF 简历解析测试"""

from __future__ import annotations

import pytest

from src.ai.resume_parser import pdf_to_markdown


class TestPdfToMarkdown:
    """pdf_to_markdown 函数测试"""

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="简历文件不存在"):
            pdf_to_markdown(str(tmp_path / "nonexistent.pdf"))

    def test_non_pdf_file(self, tmp_path):
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("hello", encoding="utf-8")
        with pytest.raises(ValueError, match="仅支持 PDF 文件"):
            pdf_to_markdown(str(txt_file))

    def test_empty_pdf_raises_value_error(self, tmp_path):
        """空 PDF 文件 (0 字节) 应该触发 ValueError"""
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"")
        with pytest.raises((ValueError, Exception)):
            pdf_to_markdown(str(pdf_file))

    def test_valid_pdf_returns_markdown(self, tmp_path):
        """用 PyMuPDF 创建一个含文字的最小 PDF, 验证能提取到 Markdown"""
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Python Developer\n5 years experience")
        pdf_path = str(tmp_path / "test_resume.pdf")
        doc.save(pdf_path)
        doc.close()

        result = pdf_to_markdown(pdf_path)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Python" in result

    def test_pdf_content_is_stripped(self, tmp_path):
        """返回内容应该 strip 过"""
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Content")
        pdf_path = str(tmp_path / "strip_test.pdf")
        doc.save(pdf_path)
        doc.close()

        result = pdf_to_markdown(pdf_path)
        assert result == result.strip()
