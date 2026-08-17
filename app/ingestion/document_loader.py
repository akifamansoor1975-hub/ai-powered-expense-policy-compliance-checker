from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_policy_pdf(file_path: str | Path) -> list[Document]:
    loader = PyPDFLoader(str(file_path))
    return loader.load()