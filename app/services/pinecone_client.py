from pinecone import Pinecone, ServerlessSpec

from app.config.settings import settings
from app.ingestion.embedder import generate_embeddings
from app.models.policy import PolicyChunkMetadata

PROBE_TEXT = "policy embedding dimension probe"
DEFAULT_CLOUD = "aws"


def get_pinecone_client() -> Pinecone:
    return Pinecone(api_key=settings.pinecone_api_key)


def get_index_dimension() -> int:
    embedding = generate_embeddings([PROBE_TEXT])[0]
    return len(embedding)


def get_pinecone_index():
    return get_pinecone_client().Index(settings.pinecone_index_name)


def ensure_pinecone_index() -> None:
    client = get_pinecone_client()
    if settings.pinecone_index_name not in client.list_indexes().names():
        client.create_index(
            name=settings.pinecone_index_name,
            dimension=get_index_dimension(),
            metric="cosine",
            spec=ServerlessSpec(cloud=DEFAULT_CLOUD, region=settings.pinecone_environment),
        )


def upsert_chunk_vectors(
    metadata_records: list[PolicyChunkMetadata],
    embeddings: list[list[float]],
) -> int:
    if not metadata_records:
        return 0
    if len(metadata_records) != len(embeddings):
        raise ValueError("metadata_records and embeddings must have the same length")
    index = get_pinecone_index()
    vectors = []
    for record, embedding in zip(metadata_records, embeddings):
        vector_metadata = {
            "chunk_id": record.chunk_id,
            "version_id": record.version_id,
            "source_document": record.source_document,
            "text": record.text,
        }
        if record.section_reference is not None:
            vector_metadata["section_reference"] = record.section_reference
        vectors.append({"id": record.chunk_id, "values": embedding, "metadata": vector_metadata})
    index.upsert(vectors=vectors)
    return len(vectors)