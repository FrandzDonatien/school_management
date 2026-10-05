from dataclasses import dataclass
from typing import Optional

from app.models import row_to


@dataclass
class SchoolYear:
    id: Optional[int] = None
    libelle: str = ""

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
