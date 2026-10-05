from dataclasses import dataclass
from typing import Optional

from app.models import row_to


@dataclass
class Subject:
    id: Optional[int] = None
    nom: str = ""
    coefficient: float = 1.0
    code: str = ""
    categorie_id: Optional[int] = None
    annee_id: Optional[int] = None

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)