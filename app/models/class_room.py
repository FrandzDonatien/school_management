from dataclasses import dataclass
from typing import Optional

from app.models import row_to


@dataclass
class ClassRoom:
    id: Optional[int] = None
    nom: str = ""
    niveau: Optional[str] = None
    prof_titulaire: str = ""
    titulaire_id: Optional[int] = None
    annee_id: Optional[int] = None

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
