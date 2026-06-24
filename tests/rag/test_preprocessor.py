# tests/rag/test_preprocessor.py
from src.rag.collector import RawDocument
from src.rag.preprocessor import Preprocessor, CleanDocument


def _code_doc(**kw) -> RawDocument:
    d = dict(
        source="github", doc_type="code",
        doc_id="src/main.py", title="main.py",
        content="def hello():\n    print('hello world')\n\n\n\n\ndef bye():\n    pass\n",
        url="http://ghe/main.py", date="2026-06-01T00:00:00", language="python",
    )
    d.update(kw)
    return RawDocument(**d)


def _doc_doc(**kw) -> RawDocument:
    d = dict(
        source="confluence", doc_type="document",
        doc_id="P-123", title="API 가이드",
        content=(
            "<h2>소개</h2><p>이 문서는 API 가이드입니다.&nbsp;참고하세요.</p>"
            "<h2>설치 방법</h2><p>pip install 명령어를 사용하여 설치합니다. "
            "가상환경 설정 후 requirements.txt를 참고하세요.</p>"
        ),
        url="http://confluence/P-123", date="2026-05-01", language="ko",
    )
    d.update(kw)
    return RawDocument(**d)


def _cr_doc(**kw) -> RawDocument:
    d = dict(
        source="doodream", doc_type="cr_record",
        doc_id="CR-2026-0001", title="테스트 CR",
        content="CR ID: CR-2026-0001\n제목: 테스트\n설명: 충분한 내용입니다 " * 3,
        url="doodream://cr/CR-2026-0001", date="2026-06-10T09:00:00", language="ko",
    )
    d.update(kw)
    return RawDocument(**d)


class TestPreprocessor:
    def setup_method(self):
        self.pp = Preprocessor()

    def test_process_code_returns_clean_doc(self):
        result = self.pp.process(_code_doc())
        assert result is not None
        assert isinstance(result, CleanDocument)
        assert result.source == "github"
        assert result.char_count > 0

    def test_process_code_normalizes_blank_lines(self):
        result = self.pp.process(_code_doc())
        assert "\n\n\n" not in result.content

    def test_binary_file_filtered(self):
        result = self.pp.process(_code_doc(doc_id="assets/logo.png", content="binary content"))
        assert result is None

    def test_empty_content_filtered(self):
        result = self.pp.process(_code_doc(content="   \n\n  "))
        assert result is None

    def test_short_content_filtered(self):
        result = self.pp.process(_code_doc(content="hi"))
        assert result is None

    def test_process_document_removes_html_tags(self):
        result = self.pp.process(_doc_doc())
        assert result is not None, "Confluence 문서가 None — 내용이 너무 짧을 수 있음"
        assert "<h2>" not in result.content
        assert "<p>" not in result.content

    def test_process_document_converts_entities(self):
        result = self.pp.process(_doc_doc())
        assert result is not None
        assert "&nbsp;" not in result.content

    def test_process_cr_returns_clean_doc(self):
        result = self.pp.process(_cr_doc())
        assert result is not None
        assert result.doc_id == "CR-2026-0001"
        assert result.language == "ko"

    def test_process_all_returns_all_valid(self):
        docs = [_code_doc(), _doc_doc(), _cr_doc()]
        results = self.pp.process_all(docs)
        assert len(results) == 3

    def test_process_all_skips_invalid(self):
        docs = [_code_doc(content="x"), _doc_doc(), _cr_doc()]
        results = self.pp.process_all(docs)
        assert len(results) == 2

    def test_normalize_date_iso(self):
        assert Preprocessor._normalize_date("2026-06-01T09:00:00") == "2026-06-01T09:00:00"

    def test_normalize_date_empty(self):
        assert Preprocessor._normalize_date("") == ""

    def test_normalize_date_invalid(self):
        assert Preprocessor._normalize_date("오늘") == ""
