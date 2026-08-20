import os

os.environ.setdefault("LLM_API_KEY", "test-llm-key")
os.environ.setdefault("LLM_MODEL_NAME", "test-model")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("PINECONE_INDEX_NAME", "test-index")
os.environ.setdefault("PINECONE_ENVIRONMENT", "test-region")
os.environ.setdefault("EMBEDDING_MODEL_NAME", "test-embedding-model")
os.environ.setdefault("EMBEDDING_API_KEY", "test-embedding-key")

from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from app.models.expense import ExpenseClaim
from app.models.policy import PolicyChunkMetadata
from app.retrieval.retriever import (
    DEFAULT_MIN_RELEVANCE_SCORE,
    DEFAULT_TOP_K,
    RetrievalResult,
    build_retrieval_query,
    embed_retrieval_query,
    retrieve_evidence,
    retrieve_relevant_chunks,
)


def make_expense(description: str | None = "Flight to conference") -> ExpenseClaim:
    return ExpenseClaim(
        category="Travel",
        amount=250.0,
        expense_date=date(2026, 1, 15),
        description=description,
    )


def make_match(chunk_id, metadata, score=0.9):
    return SimpleNamespace(id=chunk_id, score=score, metadata=metadata)


class TestBuildRetrievalQuery(TestCase):
    def test_combines_category_and_description(self):
        self.assertEqual(
            build_retrieval_query(make_expense()),
            "Travel Flight to conference",
        )

    def test_uses_category_only_when_description_missing(self):
        self.assertEqual(
            build_retrieval_query(make_expense(description=None)),
            "Travel",
        )

    def test_uses_category_only_when_description_blank(self):
        self.assertEqual(
            build_retrieval_query(make_expense(description="   ")),
            "Travel",
        )


class TestEmbedRetrievalQuery(TestCase):
    def test_returns_first_embedding_from_generate_embeddings(self):
        expected = [0.1, 0.2, 0.3]
        with patch(
            "app.retrieval.retriever.generate_embeddings",
            return_value=[expected],
        ) as mock_generate:
            result = embed_retrieval_query(make_expense())
        self.assertEqual(result, expected)
        mock_generate.assert_called_once_with(["Travel Flight to conference"])


class TestRetrieveRelevantChunks(TestCase):
    def test_embeds_query_and_passes_vector_filter_and_top_k(self):
        query_vector = [0.5, 0.6, 0.7]
        index = MagicMock()
        index.query.return_value = SimpleNamespace(matches=[])
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=query_vector,
        ) as mock_embed, patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            retrieve_relevant_chunks(make_expense(), version_id="v-123")

        mock_embed.assert_called_once_with(make_expense())
        index.query.assert_called_once_with(
            vector=query_vector,
            top_k=DEFAULT_TOP_K,
            filter={"version_id": "v-123"},
            include_metadata=True,
        )

    def test_returns_policy_chunk_metadata_preserving_fields(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match(
                    "chunk-a",
                    {
                        "chunk_id": "chunk-a",
                        "version_id": "v-123",
                        "source_document": "policy_v2.pdf",
                        "section_reference": "Section 3.1",
                        "text": "Travel expenses require itemized receipts.",
                    },
                ),
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_relevant_chunks(make_expense(), version_id="v-123")

        self.assertIsInstance(result[0], PolicyChunkMetadata)
        self.assertEqual(result[0].chunk_id, "chunk-a")
        self.assertEqual(result[0].version_id, "v-123")
        self.assertEqual(result[0].source_document, "policy_v2.pdf")
        self.assertEqual(result[0].section_reference, "Section 3.1")
        self.assertEqual(result[0].text, "Travel expenses require itemized receipts.")

    def test_section_reference_is_none_when_absent(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match(
                    "chunk-b",
                    {
                        "chunk_id": "chunk-b",
                        "version_id": "v-123",
                        "source_document": "policy_v2.pdf",
                        "text": "Meals are reimbursable up to limits.",
                    },
                ),
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_relevant_chunks(make_expense(), version_id="v-123")

        self.assertIsNone(result[0].section_reference)

    def test_never_returns_more_than_top_k(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match(
                    f"chunk-{i}",
                    {
                        "chunk_id": f"chunk-{i}",
                        "version_id": "v-123",
                        "source_document": "policy_v2.pdf",
                        "text": f"text {i}",
                    },
                )
                for i in range(7)
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_relevant_chunks(make_expense(), version_id="v-123")

        self.assertEqual(len(result), DEFAULT_TOP_K)
        self.assertEqual(
            [chunk.chunk_id for chunk in result],
            [f"chunk-{i}" for i in range(DEFAULT_TOP_K)],
        )

    def test_empty_matches_return_empty_list(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(matches=[])
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_relevant_chunks(make_expense(), version_id="v-123")

        self.assertEqual(result, [])


def standard_metadata(chunk_id, text):
    return {
        "chunk_id": chunk_id,
        "version_id": "v-123",
        "source_document": "policy_v2.pdf",
        "text": text,
    }


class TestRetrieveEvidence(TestCase):
    def test_no_matches_returns_explicit_no_evidence(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(matches=[])
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_evidence(make_expense(), version_id="v-123")

        self.assertIsInstance(result, RetrievalResult)
        self.assertTrue(result.no_evidence)
        self.assertEqual(result.chunks, [])

    def test_all_matches_below_threshold_returns_no_evidence(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match("low-1", standard_metadata("low-1", "unrelated"), score=0.05),
                make_match("low-2", standard_metadata("low-2", "also unrelated"), score=0.1),
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_evidence(make_expense(), version_id="v-123")

        self.assertTrue(result.no_evidence)
        self.assertEqual(result.chunks, [])

    def test_relevant_match_returns_evidence_and_preserves_metadata(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match("low-1", standard_metadata("low-1", "unrelated"), score=0.05),
                make_match(
                    "good-1",
                    {
                        "chunk_id": "good-1",
                        "version_id": "v-123",
                        "source_document": "policy_v2.pdf",
                        "section_reference": "Section 3.1",
                        "text": "Travel expenses require itemized receipts.",
                    },
                    score=0.85,
                ),
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ) as mock_embed, patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_evidence(make_expense(), version_id="v-123")

        mock_embed.assert_called_once_with(make_expense())
        self.assertFalse(result.no_evidence)
        self.assertEqual([chunk.chunk_id for chunk in result.chunks], ["good-1"])
        self.assertEqual(result.chunks[0].section_reference, "Section 3.1")
        self.assertEqual(result.chunks[0].text, "Travel expenses require itemized receipts.")

    def test_score_equal_to_threshold_counts_as_evidence(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match(
                    "edge-1",
                    standard_metadata("edge-1", "borderline"),
                    score=DEFAULT_MIN_RELEVANCE_SCORE,
                ),
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_evidence(make_expense(), version_id="v-123")

        self.assertFalse(result.no_evidence)
        self.assertEqual([chunk.chunk_id for chunk in result.chunks], ["edge-1"])

    def test_custom_min_score_is_respected(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(
            matches=[
                make_match("mid-1", standard_metadata("mid-1", "somewhat relevant"), score=0.85),
            ]
        )
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_evidence(make_expense(), version_id="v-123", min_score=0.9)

        self.assertTrue(result.no_evidence)

    def test_passes_filter_and_top_k_to_pinecone(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(matches=[])
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.5, 0.6, 0.7],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            retrieve_evidence(make_expense(), version_id="v-123")

        index.query.assert_called_once_with(
            vector=[0.5, 0.6, 0.7],
            top_k=DEFAULT_TOP_K,
            filter={"version_id": "v-123"},
            include_metadata=True,
        )

    def test_empty_matches_does_not_raise(self):
        index = MagicMock()
        index.query.return_value = SimpleNamespace(matches=[])
        with patch(
            "app.retrieval.retriever.embed_retrieval_query",
            return_value=[0.1],
        ), patch(
            "app.retrieval.retriever.get_pinecone_index",
            return_value=index,
        ):
            result = retrieve_evidence(make_expense(), version_id="v-123")

        self.assertTrue(result.no_evidence)
