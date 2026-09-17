"""
test_rag.py — Tests for the RAG pipeline (runbook search).
Uses mocked Pinecone and local runbook files.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRunbookLoading:
    """Tests for markdown runbook loading and chunking."""

    def test_runbooks_exist(self):
        """All expected runbook files should exist."""
        runbook_dir = Path(__file__).parent.parent / "data" / "runbooks"
        expected = [
            "payment_gateway_timeout.md",
            "payment_failure.md",
            "duplicate_payment.md",
            "failed_refund.md",
            "account_lock.md",
            "incident_escalation.md",
        ]
        for filename in expected:
            path = runbook_dir / filename
            assert path.exists(), f"Missing runbook: {filename}"

    def test_runbook_content_not_empty(self):
        """Runbooks should have substantial content."""
        runbook_dir = Path(__file__).parent.parent / "data" / "runbooks"
        for md_file in runbook_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            assert len(content) > 200, f"Runbook too short: {md_file.name}"

    def test_payment_gateway_runbook_has_symptoms(self):
        """Payment gateway runbook should contain symptom keywords."""
        runbook_dir = Path(__file__).parent.parent / "data" / "runbooks"
        content = (runbook_dir / "payment_gateway_timeout.md").read_text(encoding="utf-8")
        assert "PAYMENT_GATEWAY_TIMEOUT" in content
        assert "Investigation" in content
        assert "Recommended" in content

    def test_chunking_produces_multiple_chunks(self):
        """Large runbooks should be split into multiple chunks."""
        from backend.rag import _load_markdown_files, _chunk_document
        runbook_dir = Path(__file__).parent.parent / "data" / "runbooks"
        docs = _load_markdown_files(runbook_dir)
        assert len(docs) >= 6

        # The payment gateway runbook is large enough to chunk
        gw_doc = next(d for d in docs if d["source"] == "payment_gateway_timeout")
        chunks = _chunk_document(gw_doc)
        assert len(chunks) >= 2

    def test_chunk_ids_are_unique(self):
        """Each chunk should have a unique ID."""
        from backend.rag import _prepare_all_chunks
        chunks = _prepare_all_chunks()
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk IDs found"

    def test_chunk_text_not_empty(self):
        """No chunk should have empty text."""
        from backend.rag import _prepare_all_chunks
        chunks = _prepare_all_chunks()
        for chunk in chunks:
            assert chunk["text"].strip(), f"Empty chunk from {chunk['source']}"


class TestRunbookSearch:
    """Tests for the search_runbook function."""

    def test_search_without_pinecone_returns_mock(self):
        """When Pinecone API key is not set, mock results should be returned."""
        with patch("backend.rag.settings") as mock_settings:
            mock_settings.pinecone_api_key = ""
            from backend.rag import search_runbook
            results = search_runbook("payment gateway timeout")
            assert len(results) > 0
            assert "text" in results[0]
            assert "source" in results[0]
            assert "score" in results[0]

    def test_mock_search_payment_gateway(self):
        """Mock search should return gateway runbook for timeout queries."""
        from backend.rag import _mock_runbook_results
        results = _mock_runbook_results("payment gateway timeout stripe")
        assert results[0]["source"] == "payment_gateway_timeout"

    def test_mock_search_duplicate_payment(self):
        """Mock search should return duplicate runbook for duplicate queries."""
        from backend.rag import _mock_runbook_results
        results = _mock_runbook_results("duplicate charge on account")
        assert results[0]["source"] == "duplicate_payment"

    def test_mock_search_account_lock(self):
        """Mock search should return account lock runbook for account queries."""
        from backend.rag import _mock_runbook_results
        results = _mock_runbook_results("account locked suspended")
        assert results[0]["source"] == "account_lock"

    def test_search_result_has_required_fields(self):
        """Search results must always have required fields."""
        with patch("backend.rag.settings") as mock_settings:
            mock_settings.pinecone_api_key = ""
            from backend.rag import search_runbook
            results = search_runbook("any operational issue")
            for r in results:
                assert "source" in r
                assert "text" in r
                assert "score" in r
                assert isinstance(r["score"], float)

    def test_search_tool_wrapper(self):
        """search_runbook_tool should wrap search_runbook correctly."""
        with patch("backend.tools.search_runbook") as mock_search, \
             patch("backend.tools.audit_tool_call"), \
             patch("backend.tools.audit_tool_result"):

            mock_search.return_value = [
                {"source": "payment_gateway_timeout", "text": "Test content", "score": 0.9}
            ]
            from backend.tools import search_runbook_tool
            result = search_runbook_tool("gateway timeout")
            assert result["total_results"] == 1
            assert result["runbook_chunks"][0]["source"] == "payment_gateway_timeout"
