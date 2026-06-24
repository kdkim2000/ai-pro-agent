# tests/rag/test_pipeline.py
import os
os.environ["USE_MOCK_CONNECTORS"] = "true"

from unittest.mock import patch
from langchain_core.documents import Document

from src.rag.pipeline import RAGPipeline, PipelineResult
from src.rag.chunker import Chunker
from src.rag.preprocessor import CleanDocument


def _noop_embed(chunks):
    return [Document(page_content=c.text, metadata=c.metadata) for c in chunks]


class TestPipeline:
    def test_pipeline_collect_and_preprocess(self):
        pipeline = RAGPipeline()
        with patch.object(pipeline._embedder, 'embed_chunks', side_effect=_noop_embed), \
             patch.object(pipeline._indexer, 'ensure_collections'), \
             patch.object(pipeline._indexer, 'index_documents', return_value=[]):
            result = pipeline.run()

        assert isinstance(result, PipelineResult)
        assert sum(result.collected.values()) > 0
        assert result.preprocessed > 0

    def test_pipeline_source_filter_doodream(self):
        pipeline = RAGPipeline()
        with patch.object(pipeline._embedder, 'embed_chunks', side_effect=_noop_embed), \
             patch.object(pipeline._indexer, 'ensure_collections'), \
             patch.object(pipeline._indexer, 'index_documents', return_value=[]):
            result = pipeline.run(source="doodream")

        assert "doodream" in result.collected
        assert result.collected.get("github", 0) == 0
        assert result.collected.get("confluence", 0) == 0

    def test_pipeline_elapsed_time_recorded(self):
        pipeline = RAGPipeline()
        with patch.object(pipeline._embedder, 'embed_chunks', side_effect=_noop_embed), \
             patch.object(pipeline._indexer, 'ensure_collections'), \
             patch.object(pipeline._indexer, 'index_documents', return_value=[]):
            result = pipeline.run()

        assert result.elapsed_sec >= 0  # Mock 환경에서 거의 즉각 실행됨

    def test_pipeline_chunked_count_positive(self):
        pipeline = RAGPipeline()
        with patch.object(pipeline._embedder, 'embed_chunks', side_effect=_noop_embed), \
             patch.object(pipeline._indexer, 'ensure_collections'), \
             patch.object(pipeline._indexer, 'index_documents', return_value=[]):
            result = pipeline.run()

        assert result.chunked > 0


class TestChunker:
    def test_cr_one_chunk_per_record(self):
        doc = CleanDocument(
            source="doodream", doc_type="cr_record", doc_id="CR-001",
            title="테스트", content="CR ID: CR-001\n제목: 테스트\n설명: 충분한 내용입니다",
            url="doodream://cr/CR-001", date="2026-06-01", language="ko",
            extra={"cr_type": "new_dev", "status": "closed", "requester": "Hong", "assignee": "Kim"},
        )
        chunker = Chunker()
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].metadata["source"] == "doodream"
        assert chunks[0].metadata["cr_type"] == "new_dev"
        assert chunks[0].metadata["status"] == "closed"
        assert chunks[0].metadata["assignee"] == "Kim"
        # 두드림 미관리 항목은 메타데이터에 없어야 함
        assert "actual_hours" not in chunks[0].metadata
        assert "affected_systems" not in chunks[0].metadata

    def test_python_code_ast_chunking(self):
        content = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
        doc = CleanDocument(
            source="github", doc_type="code", doc_id="test.py",
            title="test.py", content=content,
            url="http://ghe/test.py", date="", language="python",
        )
        chunker = Chunker()
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2

    def test_document_section_chunking(self):
        content = "## 소개\n내용입니다.\n## 설치\n설치 방법입니다.\n## 사용법\n사용법입니다."
        doc = CleanDocument(
            source="confluence", doc_type="document", doc_id="P-001",
            title="가이드", content=content,
            url="http://confluence/P-001", date="2026-01-01", language="ko",
        )
        chunker = Chunker()
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 3

    def test_chunk_metadata_has_required_fields(self):
        doc = CleanDocument(
            source="doodream", doc_type="cr_record", doc_id="CR-002",
            title="CR", content="CR ID: CR-002\n제목: 테스트\n설명: 내용이 충분합니다 여기서요",
            url="doodream://cr/CR-002", date="", language="ko",
        )
        chunker = Chunker()
        chunks = chunker.chunk(doc)
        meta = chunks[0].metadata
        for key in ["source", "type", "doc_id", "title", "url"]:
            assert key in meta, f"'{key}' 키 누락"

    def test_chunk_all_aggregates_all_docs(self):
        code_doc = CleanDocument(
            source="github", doc_type="code", doc_id="a.py",
            title="a.py", content="def a():\n    return 1\n",
            url="http://ghe/a.py", date="", language="python",
        )
        cr_doc = CleanDocument(
            source="doodream", doc_type="cr_record", doc_id="CR-003",
            title="CR", content="CR ID: CR-003\n제목: 테스트\n설명: 충분합니다",
            url="doodream://cr/CR-003", date="", language="ko",
        )
        chunker = Chunker()
        chunks = chunker.chunk_all([code_doc, cr_doc])
        assert len(chunks) >= 2
