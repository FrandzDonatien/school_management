from dataclasses import dataclass
from typing import Optional

from app.models import row_to
from app.utils.formatting import person


@dataclass
class Teacher:
    id: Optional[int] = None
    nom: str = ""
    prenom: str = ""
    email: Optional[str] = None
    telephone: Optional[str] = None
    heures_sem: Optional[float] = None
    annee_id: Optional[int] = None

    @property
    def full_name(self):
        return person(self.nom, self.prenom)

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
