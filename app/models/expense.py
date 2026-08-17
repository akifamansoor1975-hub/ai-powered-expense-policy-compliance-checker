from datetime import date

from pydantic import BaseModel


class ExpenseClaim(BaseModel):
    category: str
    amount: float
    expense_date: date
    description: str | None = None