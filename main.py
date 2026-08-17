from fastapi import FastAPI

from app.config.settings import settings

app = FastAPI(title="Expense Policy Compliance Checker")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "expense-policy-compliance-checker", "llm_model": settings.llm_model_name}
