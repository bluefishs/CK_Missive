"""Tests for document_chunker — text splitting and chunk generation"""

import pytest
from app.services.ai.document.document_chunker import (
    split_into_chunks,
    build_document_text,
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
)


class TestBuildDocumentText:
    def test_all_fields(self):
        class Doc:
            subject = "道路修繕"
            content = "說明內容"
            ck_note = "備註資料"
        text = build_document_text(Doc())
        assert "主旨：道路修繕" in text
        assert "說明內容" in text
        assert "備註：備註資料" in text

    def test_missing_fields(self):
        class Doc:
            subject = "主旨"
            content = None
            ck_note = None
        text = build_document_text(Doc())
        assert "主旨：主旨" in text
        assert len(text.split("\n\n")) == 1

    def test_empty_doc(self):
        class Doc:
            subject = None
            content = None
            ck_note = None
        text = build_document_text(Doc())
        assert text == ""


class TestSplitIntoChunks:
    def test_empty_text(self):
        assert split_into_chunks("") == []
        assert split_into_chunks("   ") == []

    def test_short_text_single_chunk(self):
        text = "這是一段短文。"
        chunks = split_into_chunks(text)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_paragraph_splitting(self):
        text = "第一段內容，包含完整的說明和補充資訊。\n\n第二段內容，也有完整說明和額外描述。\n\n第三段另外的內容描述和附加說明。"
        chunks = split_into_chunks(text, max_chars=30, min_chars=10)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c["text"]) >= 10

    def test_long_paragraph_sentence_split(self):
        text = "。".join([f"第{i}句話" for i in range(50)]) + "。"
        chunks = split_into_chunks(text, max_chars=100, min_chars=20)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c["text"]) <= 100 + 50  # some tolerance for merging

    def test_sliding_window_very_long_text(self):
        text = "A" * 1000
        chunks = split_into_chunks(text, max_chars=200, min_chars=50, overlap=40)
        assert len(chunks) >= 4
        # Window chunks may merge with newline, allow some tolerance
        for c in chunks:
            assert len(c["text"]) <= 300

    def test_merge_short_segments(self):
        text = "短。\n\n也短。\n\n很短。"
        chunks = split_into_chunks(text, max_chars=200, min_chars=20)
        assert len(chunks) == 1  # all merged

    def test_chunk_positions_valid(self):
        text = "第一段。\n\n第二段。\n\n第三段。"
        chunks = split_into_chunks(text, max_chars=20, min_chars=3)
        for c in chunks:
            assert c["start_char"] >= 0
            assert c["end_char"] > c["start_char"]

    def test_real_document_simulation(self):
        text = (
            "主旨：桃園市政府工務局函\n\n"
            "說明：\n"
            "一、依據本局113年度道路養護工程計畫辦理。\n"
            "二、本案工程位於桃園區中正路段，施工期間自即日起至113年12月31日止。\n"
            "三、施工期間請用路人注意安全，如有疑問請洽本局養護工程科。\n\n"
            "備註：本案已完成環境影響評估，請相關單位配合辦理。"
        )
        chunks = split_into_chunks(text, max_chars=200, min_chars=30)
        assert len(chunks) >= 1
        total_text = " ".join(c["text"] for c in chunks)
        assert "桃園市政府" in total_text
        assert "環境影響評估" in total_text

    def test_newline_only_splitting(self):
        text = "行一\n行二\n行三\n行四\n行五"
        chunks = split_into_chunks(text, max_chars=20, min_chars=5)
        assert len(chunks) >= 1

    def test_default_params(self):
        text = "A" * 600
        chunks = split_into_chunks(text)
        for c in chunks:
            assert len(c["text"]) <= MAX_CHUNK_CHARS

    def test_chinese_punctuation_split(self):
        text = "第一段完整說明。第二段繼續描述；第三段補充。"
        chunks = split_into_chunks(text, max_chars=20, min_chars=5)
        assert len(chunks) >= 2

    def test_no_duplicate_content(self):
        text = "段落一內容。\n\n段落二內容。\n\n段落三內容。"
        chunks = split_into_chunks(text, max_chars=30, min_chars=5)
        all_text = [c["text"] for c in chunks]
        # No exact duplicates
        assert len(all_text) == len(set(all_text))
