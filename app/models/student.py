from dataclasses import dataclass
from typing import Optional

from app.models import row_to
from app.utils.formatting import person


@dataclass
class Student:
    id: Optional[int] = None
    matricule: str = ""
    nom: str = ""
    prenom: str = ""
    sexe: Optional[str] = None
    statut: str = "Nouveau"
    date_naissance: Optional[str] = None
    classe_id: Optional[int] = None
    tuteur: Optional[str] = None
    telephone: Optional[str] = None
    annee_id: Optional[int] = None

    @property
    def full_name(self):
        return person(self.nom, self.prenom)

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
