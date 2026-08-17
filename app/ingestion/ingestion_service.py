from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.chunker import chunk_policy_documents, create_chunk_metadata
from app.ingestion.document_loader import load_policy_pdf
from app.ingestion.embedder import generate_embeddings
from app.models.policy import PolicyVersion
from app.services.pinecone_client import ensure_pinecone_index, upsert_chunk_vectors
from app.services.policy_store import save_policy_version

PDF_MAGIC_BYTES = b"%PDF"


def validate_policy_upload(file, effective_date) -> None:
    if file is None:
        raise ValueError("policy file is required")
    filename = getattr(file, "filename", None) or ""
    if not filename.lower().endswith(".pdf"):
        raise ValueError("policy file must be a PDF file")
    current_position = file.tell()
    try:
        head = file.read(len(PDF_MAGIC_BYTES))
    finally:
        file.seek(current_position)
    if not head.startswith(PDF_MAGIC_BYTES):
        raise ValueError("policy file must be a PDF file")
    if effective_date is None:
        raise ValueError("effective_date is required")


def ingest_policy(upload_file, effective_date, file_path: str | Path) -> dict:
    validate_policy_upload(upload_file, effective_date)

    version_id = f"policy_{effective_date:%Y_%m}"
    source_document = getattr(upload_file, "filename", None) or Path(file_path).name

    documents = load_policy_pdf(file_path)
    chunks = chunk_policy_documents(documents)
    metadata_records = create_chunk_metadata(
        chunks,
        version_id=version_id,
        source_document=source_document,
    )
    embeddings = generate_embeddings([record.text for record in metadata_records])

    ensure_pinecone_index()
    chunks_created = upsert_chunk_vectors(metadata_records, embeddings)

    save_policy_version(
        PolicyVersion(
            version_id=version_id,
            effective_date=effective_date,
            source_document=source_document,
            uploaded_at=datetime.now(timezone.utc),
        )
    )

    return {
        "version_id": version_id,
        "effective_date": effective_date.isoformat(),
        "source_document": source_document,
        "status": "ingested",
        "chunks_created": chunks_created,
    }