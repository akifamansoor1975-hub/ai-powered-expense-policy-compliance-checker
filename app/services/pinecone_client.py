from pinecone import Pinecone, ServerlessSpec

from app.config.settings import settings
from app.ingestion.embedder import generate_embeddings

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