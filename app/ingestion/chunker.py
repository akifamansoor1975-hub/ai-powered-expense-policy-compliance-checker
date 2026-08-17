from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.policy import PolicyChunkMetadata

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


def chunk_policy_documents(
    documents: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documents)


def create_chunk_metadata(
    chunks: list[Document],
    version_id: str,
    source_document: str,
) -> list[PolicyChunkMetadata]:
    metadata_records: list[PolicyChunkMetadata] = []
    for index, chunk in enumerate(chunks):
        metadata_records.append(
            PolicyChunkMetadata(
                chunk_id=f"{version_id}_chunk_{index:04d}",
                version_id=version_id,
                source_document=source_document,
                section_reference=chunk.metadata.get("section_reference"),
                text=chunk.page_content,
            )
        )
    return metadata_records