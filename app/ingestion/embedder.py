from openai import OpenAI

from app.config.settings import settings


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = OpenAI(api_key=settings.embedding_api_key)
    response = client.embeddings.create(model=settings.embedding_model_name, input=texts)
    ordered = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered]