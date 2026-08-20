from dataclasses import dataclass

from app.ingestion.embedder import generate_embeddings
from app.models.expense import ExpenseClaim
from app.models.policy import PolicyChunkMetadata
from app.services.pinecone_client import get_pinecone_index

DEFAULT_TOP_K = 5
DEFAULT_MIN_RELEVANCE_SCORE = 0.3


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[PolicyChunkMetadata]
    no_evidence: bool


def build_retrieval_query(expense: ExpenseClaim) -> str:
    parts = [expense.category]
    if expense.description and expense.description.strip():
        parts.append(expense.description.strip())
    return " ".join(parts)


def embed_retrieval_query(expense: ExpenseClaim) -> list[float]:
    query = build_retrieval_query(expense)
    return generate_embeddings([query])[0]


def _query_matches(
    expense: ExpenseClaim,
    version_id: str,
    top_k: int = DEFAULT_TOP_K,
) -> list:
    query_embedding = embed_retrieval_query(expense)
    index = get_pinecone_index()
    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter={"version_id": version_id},
        include_metadata=True,
    )
    return response.matches[:top_k]


def _to_chunk_metadata(match) -> PolicyChunkMetadata:
    return PolicyChunkMetadata(
        chunk_id=match.id,
        version_id=match.metadata["version_id"],
        source_document=match.metadata["source_document"],
        section_reference=match.metadata.get("section_reference"),
        text=match.metadata["text"],
    )


def retrieve_relevant_chunks(
    expense: ExpenseClaim,
    version_id: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[PolicyChunkMetadata]:
    return [_to_chunk_metadata(match) for match in _query_matches(expense, version_id, top_k)]


def retrieve_evidence(
    expense: ExpenseClaim,
    version_id: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
) -> RetrievalResult:
    matches = _query_matches(expense, version_id, top_k)
    relevant_matches = [match for match in matches if match.score >= min_score]
    return RetrievalResult(
        chunks=[_to_chunk_metadata(match) for match in relevant_matches],
        no_evidence=not relevant_matches,
    )