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